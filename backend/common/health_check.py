"""
Startup health checks for all external dependencies.

Each check function returns:
  {"status": "ok" | "warn" | "fail", "message": str, "detail": dict}

Run all checks via run_all_checks(), which logs every result and returns
a summary dict. Never raises — all exceptions are caught and reported.
"""

import os
import logging
import requests
import psycopg2

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# ── helpers ──────────────────────────────────────────────────────────────────

def _ok(message: str, detail: dict = None) -> dict:
    return {"status": "ok", "message": message, "detail": detail or {}}

def _warn(message: str, detail: dict = None) -> dict:
    return {"status": "warn", "message": message, "detail": detail or {}}

def _fail(message: str, detail: dict = None) -> dict:
    return {"status": "fail", "message": message, "detail": detail or {}}


# ── individual checks ─────────────────────────────────────────────────────────

def check_azure_openai() -> dict:
    """
    Verifies both required deployments are reachable:
      - gpt-4o  (chat completions)
      - text-embedding-ada-002  (embeddings)
    Uses a single-token / tiny call to minimise cost.
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key  = os.getenv("AZURE_OPENAI_API_KEY", "")
    version  = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    chat_dep = os.getenv("AZURE_MODEL_DEPLOYMENT_NAME", "gpt-4o")
    emb_dep  = os.getenv("AZURE_EMBEDDING", "text-embedding-ada-002")

    missing = [v for v, k in [
        (endpoint, "AZURE_OPENAI_ENDPOINT"),
        (api_key,  "AZURE_OPENAI_API_KEY"),
    ] if not v]
    if missing:
        return _fail(f"Missing env vars: {missing}")

    headers = {"api-key": api_key, "Content-Type": "application/json"}
    results = {}

    # --- chat deployment ---
    try:
        url = f"{endpoint}/openai/deployments/{chat_dep}/chat/completions?api-version={version}"
        r = requests.post(url, headers=headers,
                          json={"messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                          timeout=15)
        if r.status_code == 200:
            results["chat"] = f"{chat_dep} → 200 OK"
        else:
            results["chat"] = f"{chat_dep} → {r.status_code}: {r.text[:200]}"
    except Exception as e:
        results["chat"] = f"{chat_dep} → exception: {e}"

    # --- embedding deployment ---
    try:
        url = f"{endpoint}/openai/deployments/{emb_dep}/embeddings?api-version={version}"
        r = requests.post(url, headers=headers,
                          json={"input": "health check"},
                          timeout=15)
        if r.status_code == 200:
            dims = len(r.json()["data"][0]["embedding"])
            results["embeddings"] = f"{emb_dep} → 200 OK ({dims}-dim vector)"
        else:
            results["embeddings"] = f"{emb_dep} → {r.status_code}: {r.text[:200]}"
    except Exception as e:
        results["embeddings"] = f"{emb_dep} → exception: {e}"

    any_fail = any("200" not in v for v in results.values())
    if any_fail:
        return _fail("One or more Azure OpenAI deployments unreachable", results)
    return _ok("Azure OpenAI: both deployments reachable", results)


def check_azure_search() -> dict:
    """
    Verifies the AI Search service is reachable and all 3 required indexes
    exist with at least one document. Logs a warning (not fail) for empty
    indexes — the system still runs, but output quality will be degraded.
    """
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
    key      = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")

    if not endpoint or not key:
        return _fail("Missing env vars: AZURE_SEARCH_ENDPOINT and/or AZURE_SEARCH_ADMIN_KEY")

    required_indexes = [
        "ras-helper-index-v1",
        "tcg-manual-index-v1",
        "tcg-cucumber-index-v1",
    ]

    headers = {"api-key": key}
    index_results = {}
    any_missing = False
    any_empty   = False

    for index_name in required_indexes:
        try:
            r = requests.get(
                f"{endpoint}/indexes/{index_name}/stats?api-version=2023-11-01",
                headers=headers,
                timeout=15,
            )
            if r.status_code == 200:
                doc_count = r.json().get("documentCount", 0)
                if doc_count == 0:
                    index_results[index_name] = "EXISTS but EMPTY — RAG context unavailable, output quality will be degraded"
                    any_empty = True
                else:
                    index_results[index_name] = f"{doc_count} documents"
            elif r.status_code == 404:
                index_results[index_name] = "MISSING — run DocIngestionFunction to create and seed this index"
                any_missing = True
            else:
                index_results[index_name] = f"ERROR {r.status_code}: {r.text[:200]}"
                any_missing = True
        except Exception as e:
            index_results[index_name] = f"exception: {e}"
            any_missing = True

    if any_missing:
        return _fail("One or more required AI Search indexes are missing", index_results)
    if any_empty:
        return _warn("All indexes exist but one or more are empty — agents will produce generic output", index_results)
    return _ok("Azure AI Search: all indexes present and populated", index_results)


def check_postgresql() -> dict:
    """
    Verifies:
      1. Connection succeeds (SSL required)
      2. All 3 required tables exist
      3. The critical ('TCG', 'team_prompt') row in agent_prompts exists
         (its absence causes ExecuteTCG to crash on cold start — Bug 1)
    """
    host     = os.getenv("POSTGRES_HOST", "")
    port     = os.getenv("POSTGRES_PORT", "5432")
    db       = os.getenv("POSTGRES_DB", "postgres")
    user     = os.getenv("POSTGRES_USER", "")
    password = os.getenv("POSTGRES_PASSWORD", "")

    missing_vars = [k for k, v in {
        "POSTGRES_HOST": host,
        "POSTGRES_USER": user,
        "POSTGRES_PASSWORD": password,
    }.items() if not v]
    if missing_vars:
        return _fail(f"Missing env vars: {missing_vars}")

    try:
        conn = psycopg2.connect(
            host=host, port=port, database=db,
            user=user, password=password,
            sslmode="require",
            connect_timeout=10,
        )
    except Exception as e:
        hint = ""
        if "could not connect" in str(e) or "Connection refused" in str(e):
            hint = " — check Azure PostgreSQL firewall rules (your IP may not be whitelisted)"
        elif "password authentication failed" in str(e):
            hint = " — check POSTGRES_USER / POSTGRES_PASSWORD in .env"
        return _fail(f"PostgreSQL connection failed: {e}{hint}")

    detail = {}
    warnings = []

    try:
        cur = conn.cursor()

        # Table existence
        required_tables = ["agent_prompts", "user_request_logs", "user_feedback"]
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        existing = {row[0] for row in cur.fetchall()}
        for t in required_tables:
            if t in existing:
                detail[t] = "exists"
            else:
                detail[t] = "MISSING — run DDL from docs/05_deployment.md"
                warnings.append(f"table '{t}' missing")

        # Critical TCG prompt row
        cur.execute(
            "SELECT COUNT(*) FROM agent_prompts WHERE ai_helper_name = %s AND agent_name = %s",
            ("TCG", "team_prompt"),
        )
        tcg_count = cur.fetchone()[0]
        if tcg_count == 0:
            detail["agent_prompts ('TCG','team_prompt')"] = (
                "MISSING — ExecuteTCG will crash on cold start (Bug 1 in docs/04_component_status.md)"
            )
            warnings.append("TCG team_prompt row missing — ExecuteTCG cold-start crash risk")
        else:
            detail["agent_prompts ('TCG','team_prompt')"] = f"{tcg_count} row(s) found"

        conn.close()
    except Exception as e:
        conn.close()
        return _fail(f"PostgreSQL query failed after connecting: {e}", detail)

    if warnings:
        return _warn(f"PostgreSQL connected but issues found: {'; '.join(warnings)}", detail)
    return _ok("PostgreSQL: connected, all tables present, critical prompt row exists", detail)


def check_blob_storage() -> dict:
    """
    Verifies the Azure Storage account is reachable and at least one
    container exists (needed for DocIngestionFunction CSV uploads).
    """
    account_name = os.getenv("STORAGE_ACCOUNT_NAME", "")
    account_key  = os.getenv("STORAGE_ACCOUNT_KEY", "")

    if not account_name or not account_key:
        return _fail("Missing env vars: STORAGE_ACCOUNT_NAME and/or STORAGE_ACCOUNT_KEY")

    try:
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            credential=account_key,
        )
        containers = [c["name"] for c in client.list_containers()]
        if not containers:
            return _warn(
                f"Blob Storage reachable but no containers found in '{account_name}' "
                "— create a container before running DocIngestionFunction",
                {"account": account_name, "containers": []},
            )
        return _ok(
            f"Azure Blob Storage: reachable, {len(containers)} container(s) found",
            {"account": account_name, "containers": containers},
        )
    except Exception as e:
        hint = ""
        if "AuthenticationFailed" in str(e):
            hint = " — check STORAGE_ACCOUNT_KEY in .env"
        elif "ResourceNotFound" in str(e):
            hint = " — check STORAGE_ACCOUNT_NAME in .env"
        return _fail(f"Blob Storage check failed: {e}{hint}")


# ── orchestrator ──────────────────────────────────────────────────────────────

def run_all_checks() -> dict:
    """
    Runs every health check, logs each result, and returns a summary dict.

    Format:
      {
        "overall": "ok" | "warn" | "fail",
        "checks": {
          "azure_openai":  {"status": ..., "message": ..., "detail": ...},
          "azure_search":  {...},
          "postgresql":    {...},
          "blob_storage":  {...},
        }
      }

    "fail" in any check → overall = "fail"
    "warn" in any check (no fails) → overall = "warn"
    all "ok" → overall = "ok"
    """
    checks = {
        "azure_openai": check_azure_openai,
        "azure_search": check_azure_search,
        "postgresql":   check_postgresql,
        "blob_storage": check_blob_storage,
    }

    results = {}
    logger.info("=" * 60)
    logger.info("SDLC-AGENTS STARTUP HEALTH CHECK")
    logger.info("=" * 60)

    for name, fn in checks.items():
        try:
            result = fn()
        except Exception as e:
            result = _fail(f"Health check function raised unexpectedly: {e}")

        results[name] = result
        status  = result["status"].upper()
        message = result["message"]
        detail  = result.get("detail", {})

        log_fn = logger.info if status == "OK" else (logger.warning if status == "WARN" else logger.error)
        log_fn(f"[{status:4s}] {name}: {message}")
        for k, v in detail.items():
            log_fn(f"         {k}: {v}")

    statuses = [r["status"] for r in results.values()]
    if "fail" in statuses:
        overall = "fail"
    elif "warn" in statuses:
        overall = "warn"
    else:
        overall = "ok"

    logger.info("-" * 60)
    logger.info(f"OVERALL: {overall.upper()}")
    logger.info("=" * 60)

    return {"overall": overall, "checks": results}
