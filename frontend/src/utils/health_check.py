"""
Frontend startup health checks.

Checks every external dependency the frontend touches directly:
  - PostgreSQL (logging)
  - Jira endpoint reachability (pre-auth connectivity)
  - Azure Function App reachability

Run once at startup via run_frontend_checks().
Results are cached in st.session_state so the sidebar panel doesn't
re-run on every Streamlit rerender.

Each check returns:
  {"status": "ok" | "warn" | "fail", "message": str, "detail": dict}
"""

import os
import logging
import requests
import psycopg2

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _ok(message: str, detail: dict = None) -> dict:
    return {"status": "ok", "message": message, "detail": detail or {}}

def _warn(message: str, detail: dict = None) -> dict:
    return {"status": "warn", "message": message, "detail": detail or {}}

def _fail(message: str, detail: dict = None) -> dict:
    return {"status": "fail", "message": message, "detail": detail or {}}


# ── individual checks ─────────────────────────────────────────────────────────

def check_postgresql() -> dict:
    """Verify the frontend can connect to PostgreSQL for audit logging."""
    host     = os.getenv("POSTGRES_HOST", "")
    port     = os.getenv("POSTGRES_PORT", "5432")
    db       = os.getenv("POSTGRES_DB", "postgres")
    user     = os.getenv("POSTGRES_USER", "")
    password = os.getenv("POSTGRES_PASSWORD", "")

    missing = [k for k, v in {
        "POSTGRES_HOST": host,
        "POSTGRES_USER": user,
        "POSTGRES_PASSWORD": password,
    }.items() if not v]
    if missing:
        return _fail(
            f"Missing env vars: {missing} — request/feedback logging will not work",
            {"missing": missing},
        )

    try:
        conn = psycopg2.connect(
            host=host, port=port, database=db,
            user=user, password=password,
            sslmode="require",
            connect_timeout=8,
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
        tables = {row[0] for row in cur.fetchall()}
        conn.close()

        missing_tables = [t for t in ["user_request_logs", "user_feedback"] if t not in tables]
        if missing_tables:
            return _warn(
                f"PostgreSQL connected but tables missing: {missing_tables} — logging will fail at runtime",
                {"missing_tables": missing_tables, "existing": list(tables)},
            )
        return _ok("PostgreSQL: connected, logging tables present")
    except Exception as e:
        hint = ""
        if "could not connect" in str(e) or "Connection refused" in str(e):
            hint = " — check Azure PostgreSQL firewall (your IP may be blocked)"
        elif "password authentication failed" in str(e):
            hint = " — check POSTGRES_USER / POSTGRES_PASSWORD in .env"
        return _fail(
            f"PostgreSQL connection failed: {e}{hint} — request/feedback logging will not work"
        )


def check_jira_endpoint() -> dict:
    """
    Verify the Jira base URL is reachable (unauthenticated).
    Does NOT validate credentials — just checks connectivity.
    A 401 response still means the server is up.
    """
    jira_endpoint = os.getenv("JIRA_ENDPOINT", "").rstrip("/")
    proj_key      = os.getenv("PROJ_KEY", "")

    if not jira_endpoint:
        return _fail(
            "JIRA_ENDPOINT not set — Jira ID lookup and push to Jira will not work"
        )

    detail = {"endpoint": jira_endpoint}
    if not proj_key:
        detail["PROJ_KEY"] = "NOT SET — TCG push will fail (project key required)"

    try:
        r = requests.get(
            f"{jira_endpoint}/rest/api/2/serverInfo",
            timeout=10,
            verify=False,
        )
        if r.status_code == 200:
            info = r.json()
            detail.update({
                "jira_version": info.get("version", "unknown"),
                "server_title": info.get("serverTitle", "unknown"),
            })
            if not proj_key:
                return _warn(
                    "Jira server reachable but PROJ_KEY not set — TCG push will fail",
                    detail,
                )
            return _ok(f"Jira: server reachable (v{info.get('version','?')})", detail)
        elif r.status_code == 401:
            # Server is up, auth is handled separately at login
            return _ok(
                "Jira: server reachable (auth required — will validate at login)",
                {**detail, "http_status": 401},
            )
        else:
            return _warn(
                f"Jira: unexpected response {r.status_code} — server may be degraded",
                {**detail, "http_status": r.status_code, "body": r.text[:200]},
            )
    except requests.exceptions.ConnectionError:
        return _fail(
            f"Jira: cannot reach {jira_endpoint} — check JIRA_ENDPOINT in .env or network connectivity"
        )
    except Exception as e:
        return _fail(f"Jira connectivity check failed: {e}")


def check_azure_function_app() -> dict:
    """
    Verify the Azure Function App URL is set and reachable.
    Sends a lightweight GET to the base URL — not a full trigger.
    """
    app_url = os.getenv("AZURE_FUNCTION_APP", "").rstrip("/")

    if not app_url:
        return _fail(
            "AZURE_FUNCTION_APP not set — all AI agent calls will fail"
        )

    # Detect local dev vs cloud
    is_local = "localhost" in app_url or "127.0.0.1" in app_url
    label    = "local Azure Functions" if is_local else "Azure Function App"

    try:
        # A GET to the orchestrator endpoint returns 400 (missing body) or 405 (method not allowed)
        # when the function is running — both still prove the host is up.
        test_url = f"{app_url}/api/DurableFunctionsOrchestrator"
        r = requests.get(test_url, timeout=8)
        if r.status_code in (200, 202, 400, 405):
            return _ok(f"{label}: reachable at {app_url}", {"http_status": r.status_code})
        elif r.status_code == 404:
            return _warn(
                f"{label}: host reached but function not found — may not be deployed yet",
                {"url": app_url, "http_status": 404},
            )
        else:
            return _warn(
                f"{label}: unexpected response {r.status_code}",
                {"url": app_url, "http_status": r.status_code},
            )
    except requests.exceptions.ConnectionError:
        if is_local:
            return _fail(
                f"Local Azure Functions not running — start with: cd backend && func start"
            )
        return _fail(
            f"Cannot reach Azure Function App at {app_url} — check AZURE_FUNCTION_APP in .env"
        )
    except Exception as e:
        return _fail(f"Azure Function App check failed: {e}")


# ── orchestrator ──────────────────────────────────────────────────────────────

def run_frontend_checks() -> dict:
    """
    Runs all frontend health checks, logs every result, returns summary dict.

    Format:
      {
        "overall": "ok" | "warn" | "fail",
        "checks": {
          "postgresql":          {...},
          "jira_endpoint":       {...},
          "azure_function_app":  {...},
        }
      }
    """
    checks = {
        "postgresql":         check_postgresql,
        "jira_endpoint":      check_jira_endpoint,
        "azure_function_app": check_azure_function_app,
    }

    results = {}
    logger.info("=" * 55)
    logger.info("SDLC-AGENTS FRONTEND STARTUP HEALTH CHECK")
    logger.info("=" * 55)

    for name, fn in checks.items():
        try:
            result = fn()
        except Exception as e:
            result = _fail(f"Health check raised unexpectedly: {e}")

        results[name] = result
        status  = result["status"].upper()
        message = result["message"]
        detail  = result.get("detail", {})

        log_fn = logger.info if status == "OK" else (logger.warning if status == "WARN" else logger.error)
        log_fn(f"[{status:4s}] {name}: {message}")
        for k, v in detail.items():
            log_fn(f"         {k}: {v}")

    statuses = [r["status"] for r in results.values()]
    overall  = "fail" if "fail" in statuses else ("warn" if "warn" in statuses else "ok")

    logger.info("-" * 55)
    logger.info(f"OVERALL: {overall.upper()}")
    logger.info("=" * 55)

    return {"overall": overall, "checks": results}
