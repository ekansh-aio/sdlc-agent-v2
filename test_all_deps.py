"""
Standalone external-dependency test for SDLC Agents.

Covers:
  1. Azure OpenAI   — gpt-4o chat + text-embedding-ada-002
  2. Azure AI Search — service reachable + 3 required indexes + doc counts
  3. PostgreSQL      — connection + required tables + critical prompt rows
  4. Azure Blob      — account reachable + containers
  5. Azure Function  — local or cloud Function App reachable
  6. Jira            — server reachable (no creds needed for connectivity)

Usage (from project root):
  frontend\.venv\Scripts\python.exe test_all_deps.py

Reads credentials from:
  - backend/local.settings.json  (backend services)
  - frontend/.env                (frontend-specific settings)
"""

import json
import os
import sys
import urllib.request
import urllib.error

# ── colour helpers ──────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(label, msg, detail=None):
    print(f"  {GREEN}[PASS]{RESET} {BOLD}{label}{RESET}: {msg}")
    if detail:
        for k, v in detail.items():
            print(f"          {k}: {v}")

def warn(label, msg, detail=None):
    print(f"  {YELLOW}[WARN]{RESET} {BOLD}{label}{RESET}: {msg}")
    if detail:
        for k, v in detail.items():
            print(f"          {k}: {v}")

def fail(label, msg, detail=None):
    print(f"  {RED}[FAIL]{RESET} {BOLD}{label}{RESET}: {msg}")
    if detail:
        for k, v in detail.items():
            print(f"          {k}: {v}")

def section(title):
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'─'*55}{RESET}")


# ── load config ─────────────────────────────────────────────────────────────

def load_env():
    """Load env vars from local.settings.json and frontend/.env."""
    root = os.path.dirname(os.path.abspath(__file__))

    # backend/local.settings.json
    settings_path = os.path.join(root, "backend", "local.settings.json")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            data = json.load(f)
        for k, v in data.get("Values", {}).items():
            os.environ.setdefault(k, str(v))

    # frontend/.env
    env_path = os.path.join(root, "frontend", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

    # root .env (fallback)
    root_env = os.path.join(root, ".env")
    if os.path.exists(root_env):
        with open(root_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

load_env()


# ── 1. Azure OpenAI ──────────────────────────────────────────────────────────

def test_azure_openai():
    section("1 · Azure OpenAI")

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key  = os.getenv("AZURE_OPENAI_API_KEY", "")
    version  = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    chat_dep = os.getenv("AZURE_MODEL_DEPLOYMENT_NAME", "gpt-4o")
    emb_dep  = os.getenv("AZURE_EMBEDDING", "text-embedding-ada-002")

    if not endpoint or not api_key:
        fail("Config", "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY not set")
        return

    headers_bytes = f"api-key: {api_key}\r\nContent-Type: application/json\r\n".encode()

    # --- gpt-4o chat ---
    try:
        import urllib.request, json as _json
        body = _json.dumps({
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 3
        }).encode()
        url = f"{endpoint}/openai/deployments/{chat_dep}/chat/completions?api-version={version}"
        req = urllib.request.Request(url, data=body,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = _json.loads(r.read())
            reply = resp["choices"][0]["message"]["content"].strip()
            ok("gpt-4o chat", f"deployment '{chat_dep}' responded: '{reply}'")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        fail("gpt-4o chat", f"HTTP {e.code}: {body[:300]}")
    except Exception as e:
        fail("gpt-4o chat", str(e))

    # --- text-embedding-ada-002 ---
    try:
        body = _json.dumps({"input": "health check"}).encode()
        url = f"{endpoint}/openai/deployments/{emb_dep}/embeddings?api-version={version}"
        req = urllib.request.Request(url, data=body,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = _json.loads(r.read())
            dims = len(resp["data"][0]["embedding"])
            ok("embeddings", f"deployment '{emb_dep}' returned {dims}-dim vector")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        fail("embeddings", f"HTTP {e.code}: {body[:300]}")
    except Exception as e:
        fail("embeddings", str(e))


# ── 2. Azure AI Search ───────────────────────────────────────────────────────

def test_azure_search():
    section("2 · Azure AI Search")

    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
    key      = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")

    if not endpoint or not key:
        fail("Config", "AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_ADMIN_KEY not set")
        return

    # service reachable
    try:
        import urllib.request, json as _json
        req = urllib.request.Request(
            f"{endpoint}/indexes?api-version=2023-11-01&$select=name",
            headers={"api-key": key})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = _json.loads(r.read())
            existing = {idx["name"] for idx in data.get("value", [])}
            ok("service", f"reachable at {endpoint} ({len(existing)} indexes total)")
    except urllib.error.HTTPError as e:
        fail("service", f"HTTP {e.code}: {e.read().decode()[:300]}")
        return
    except Exception as e:
        fail("service", str(e))
        return

    # individual indexes
    required = [
        "ras-helper-index-v1",
        "tcg-manual-index-v1",
        "tcg-cucumber-index-v1",
    ]
    for idx_name in required:
        try:
            req = urllib.request.Request(
                f"{endpoint}/indexes/{idx_name}/stats?api-version=2023-11-01",
                headers={"api-key": key})
            with urllib.request.urlopen(req, timeout=15) as r:
                stats = _json.loads(r.read())
                doc_count = stats.get("documentCount", 0)
                storage_kb = stats.get("storageSize", 0) // 1024
                if doc_count == 0:
                    warn(idx_name, f"index exists but is EMPTY — run DocIngestionFunction to seed it")
                else:
                    ok(idx_name, f"{doc_count} documents, {storage_kb} KB")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                fail(idx_name, "index MISSING — run DocIngestionFunction to create and seed it")
            else:
                fail(idx_name, f"HTTP {e.code}: {e.read().decode()[:200]}")
        except Exception as e:
            fail(idx_name, str(e))


# ── 3. PostgreSQL ────────────────────────────────────────────────────────────

def test_postgresql():
    section("3 · PostgreSQL")

    host     = os.getenv("POSTGRES_HOST", "")
    port     = os.getenv("POSTGRES_PORT", "5432")
    db       = os.getenv("POSTGRES_DB", "postgres")
    user     = os.getenv("POSTGRES_USER", "")
    password = os.getenv("POSTGRES_PASSWORD", "")

    if not host or not user or not password:
        fail("Config", "POSTGRES_HOST / POSTGRES_USER / POSTGRES_PASSWORD not set")
        return

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        fail("psycopg2", "psycopg2 not installed — run: pip install psycopg2-binary")
        return

    try:
        conn = psycopg2.connect(
            host=host, port=port, database=db,
            user=user, password=password,
            sslmode="require", connect_timeout=10)
        ok("connection", f"connected to {host}/{db} as {user}")
    except Exception as e:
        hint = ""
        if "could not connect" in str(e) or "refused" in str(e):
            hint = " — check Azure PostgreSQL firewall rules (whitelist your IP)"
        elif "password" in str(e):
            hint = " — check POSTGRES_USER / POSTGRES_PASSWORD"
        fail("connection", f"{e}{hint}")
        return

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    existing = {r["table_name"] for r in cur.fetchall()}

    required_tables = ["agent_prompts", "user_request_logs", "maintenance_notice"]
    for t in required_tables:
        if t in existing:
            cur.execute(f"SELECT COUNT(*) AS n FROM {t}")
            n = cur.fetchone()["n"]
            ok(f"table: {t}", f"{n} row(s)")
        else:
            fail(f"table: {t}", "MISSING — run DDL from docs/05_deployment.md")

    # critical prompt rows
    prompts_needed = [
        ("RAS", "RequestHandlerAgent"),
        ("RAS", "AnalyserAgent"),
        ("RAS", "ReviewerAgent"),
        ("RAS", "FinalResponseGeneratorAgent"),
        ("RAS", "team_prompt"),
        ("TCG", "team_prompt"),
    ]
    for helper, agent in prompts_needed:
        if "agent_prompts" not in existing:
            break
        cur.execute(
            "SELECT COUNT(*) AS n FROM agent_prompts WHERE ai_helper_name=%s AND agent_name=%s",
            (helper, agent))
        n = cur.fetchone()["n"]
        label = f"agent_prompts ({helper}, {agent})"
        if n > 0:
            ok(label, f"{n} row(s)")
        else:
            sev = fail if (helper == "TCG" and agent == "team_prompt") else warn
            sev(label, "MISSING — agents may crash or produce wrong output")

    conn.close()


# ── 4. Azure Blob Storage ────────────────────────────────────────────────────

def test_blob_storage():
    section("4 · Azure Blob Storage")

    account_name = os.getenv("STORAGE_ACCOUNT_NAME", "")
    account_key  = os.getenv("STORAGE_ACCOUNT_KEY", "")

    if not account_name or not account_key:
        fail("Config", "STORAGE_ACCOUNT_NAME or STORAGE_ACCOUNT_KEY not set")
        return

    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        fail("azure-storage-blob", "not installed — run: pip install azure-storage-blob")
        return

    try:
        client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            credential=account_key)
        containers = [c["name"] for c in client.list_containers()]
        if not containers:
            warn("containers", f"account '{account_name}' is reachable but has NO containers — DocIngestionFunction will fail")
        else:
            ok("account", f"'{account_name}' reachable, {len(containers)} container(s): {', '.join(containers)}")
    except Exception as e:
        hint = ""
        if "AuthenticationFailed" in str(e):
            hint = " — check STORAGE_ACCOUNT_KEY"
        elif "ResourceNotFound" in str(e) or "does not exist" in str(e):
            hint = " — check STORAGE_ACCOUNT_NAME"
        fail("account", f"{e}{hint}")


# ── 5. Azure Function App ────────────────────────────────────────────────────

def test_function_app():
    section("5 · Azure Function App")

    app_url = os.getenv("AZURE_FUNCTION_APP", "").rstrip("/")

    if not app_url:
        fail("Config", "AZURE_FUNCTION_APP not set in frontend/.env")
        return

    is_local = "localhost" in app_url or "127.0.0.1" in app_url
    label    = "local (func start)" if is_local else "cloud"

    endpoints_to_try = [
        ("/api/DurableFunctionsOrchestrator", "DurableOrchestrator trigger"),
        ("/api/HealthCheck",                  "HealthCheck endpoint"),
    ]

    import urllib.request as _ur, urllib.error as _ue
    for path, name in endpoints_to_try:
        url = f"{app_url}{path}"
        try:
            req = _ur.Request(url, method="GET")
            with _ur.urlopen(req, timeout=8) as r:
                ok(name, f"HTTP {r.status} — {label} function app is running at {app_url}")
                break
        except _ue.HTTPError as e:
            if e.code in (200, 202, 400, 405):
                # 400/405 still means the host is up
                ok(name, f"HTTP {e.code} (host alive) — {label} function app running at {app_url}")
                break
            elif e.code == 404:
                continue  # try next endpoint
        except _ue.URLError:
            if is_local:
                fail(name, f"Cannot connect to {app_url} — run: cd backend && func start")
            else:
                fail(name, f"Cannot reach {app_url} — check AZURE_FUNCTION_APP in frontend/.env")
            return
        except Exception as e:
            fail(name, str(e))
            return
    else:
        warn("function app", f"Host responded but no known endpoints found at {app_url} — may not be deployed yet")


# ── 6. Jira ──────────────────────────────────────────────────────────────────

def test_jira():
    section("6 · Jira")

    jira_endpoint = os.getenv("JIRA_ENDPOINT", "").rstrip("/")
    proj_key      = os.getenv("PROJ_KEY", "")

    if not jira_endpoint:
        fail("Config", "JIRA_ENDPOINT not set in frontend/.env — all Jira features will be broken")
        return

    if not proj_key:
        warn("PROJ_KEY", "not set — TCG 'push to Jira' will fail (need project key)")

    import urllib.request as _ur, urllib.error as _ue
    import json as _json

    # server info (no auth needed)
    try:
        req = _ur.Request(
            f"{jira_endpoint}/rest/api/2/serverInfo",
            headers={"Accept": "application/json"})
        # disable SSL verification via context
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with _ur.urlopen(req, timeout=10, context=ctx) as r:
            info = _json.loads(r.read())
            ok("server", f"reachable — Jira {info.get('version','?')}, '{info.get('serverTitle','?')}'",
               {"url": jira_endpoint})
    except _ue.HTTPError as e:
        if e.code == 401:
            ok("server", f"reachable (returns 401 — auth enforced, login will validate credentials)",
               {"url": jira_endpoint})
        elif e.code == 403:
            warn("server", f"HTTP 403 — server up but access restricted (check IP allowlist)",
                 {"url": jira_endpoint})
        else:
            fail("server", f"HTTP {e.code}: {e.read().decode()[:200]}")
    except _ue.URLError as e:
        fail("server", f"Cannot reach {jira_endpoint} — is the URL correct? ({e.reason})")
    except Exception as e:
        fail("server", str(e))


# ── summary ──────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  SDLC AGENTS — External Dependency Tests{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")
    print(f"  Python : {sys.version.split()[0]}")
    print(f"  CWD    : {os.getcwd()}")

    test_azure_openai()
    test_azure_search()
    test_postgresql()
    test_blob_storage()
    test_function_app()
    test_jira()

    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  Done.{RESET}  Fix any {RED}[FAIL]{RESET} items before running the app.")
    print(f"  {YELLOW}[WARN]{RESET} items degrade quality but won't stop startup.")
    print(f"{BOLD}{'='*55}{RESET}\n")


if __name__ == "__main__":
    main()
