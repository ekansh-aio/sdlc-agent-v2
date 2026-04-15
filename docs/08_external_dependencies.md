# 08 — External Dependencies & Verification Guide

Everything outside the codebase itself that must be set up before the app works —
and exactly how to verify each one is ready.

---

## Dependency Map at a Glance

```
sdlc-agents needs:

  1. Azure OpenAI      ─── GPT-4o (agents) + ada-002 (embeddings)
  2. Azure AI Search   ─── 3 indexes, each seeded with data
  3. Azure PostgreSQL  ─── 3 tables created
  4. Azure Blob Storage─── container exists for CSV uploads
  5. Jira              ─── valid account + correct permissions + custom fields
  6. Jira Xray plugin  ─── installed on the Jira instance (TCG only)
  7. Azure Function App─── deployed, Durable extension present
```

If any of these are missing or misconfigured the system will fail — usually silently.
This document tells you how to check each one before writing a single line of code.

---

## 1. Azure OpenAI

### What the code needs
- `gpt-4o` deployment (for all agent chains)
- `text-embedding-ada-002` deployment (for RAG search and DocIngestion)
- Both on the same endpoint: `https://aio-az-openai-service1.openai.azure.com/`

### How to verify

**Option A — cURL (fastest)**
```bash
# Test GPT-4o chat
curl -X POST \
  "https://aio-az-openai-service1.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-01" \
  -H "api-key: <AZURE_OPENAI_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"ping"}],"max_tokens":5}'

# Expected: HTTP 200 with {"choices":[{"message":{"content":"..."}}]}
# Bad signs: 401 (wrong key), 404 (deployment name wrong), 403 (quota/region issue)
```

```bash
# Test ada-002 embeddings
curl -X POST \
  "https://aio-az-openai-service1.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-01" \
  -H "api-key: <AZURE_OPENAI_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"input":"test"}'

# Expected: HTTP 200 with {"data":[{"embedding":[...1536 floats...]}]}
```

**Option B — Python**
```python
import requests, os
from dotenv import load_dotenv
load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
key = os.getenv("AZURE_OPENAI_API_KEY")
version = os.getenv("AZURE_OPENAI_API_VERSION")

# Chat
r = requests.post(
    f"{endpoint}/openai/deployments/gpt-4o/chat/completions?api-version={version}",
    headers={"api-key": key, "Content-Type": "application/json"},
    json={"messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}
)
print("GPT-4o:", r.status_code, r.json().get("choices", r.text))

# Embeddings
r = requests.post(
    f"{endpoint}/openai/deployments/text-embedding-ada-002/embeddings?api-version={version}",
    headers={"api-key": key, "Content-Type": "application/json"},
    json={"input": "test"}
)
embedding = r.json().get("data", [{}])[0].get("embedding", [])
print("ada-002:", r.status_code, f"{len(embedding)}-dim vector" if embedding else r.text)
```

### What a passing result looks like
```
GPT-4o: 200  choices present
ada-002: 200  1536-dim vector
```

### Common failure causes
| Error | Cause | Fix |
|-------|-------|-----|
| 401 | Wrong `AZURE_OPENAI_API_KEY` | Copy key from Azure Portal → Azure OpenAI → Keys |
| 404 | Deployment name wrong | Check Portal → Azure OpenAI → Deployments — name must be exactly `gpt-4o` and `text-embedding-ada-002` |
| 429 | Rate limit / quota | Request quota increase or wait |

---

## 2. Azure AI Search

### What the code needs
- Service endpoint: `https://sdlc-test-ai-search.search.windows.net`
- 3 indexes, each with a `default` semantic configuration:
  - `ras-helper-index-v1` — must have fields: `description`, `summary`, `acceptance_criteria`, `embedding`
  - `tcg-manual-index-v1` — must have fields: `description`, `summary`, `manual_test_steps`, `embedding`
  - `tcg-cucumber-index-v1` — must have fields: `description`, `summary`, `cucumber_scenario`, `embedding`
- Each index must be **populated with data** — empty indexes return 0 results (no RAG context, silent quality drop)

### How to verify

**Step 1 — Check the service is reachable and key is valid**
```bash
curl -X GET \
  "https://sdlc-test-ai-search.search.windows.net/indexes?api-version=2023-11-01" \
  -H "api-key: <AZURE_SEARCH_ADMIN_KEY>"

# Expected: HTTP 200 with {"value":[{"name":"ras-helper-index-v1"}, ...]}
# 401 = wrong key   |   404 = wrong endpoint
```

**Step 2 — Check each index exists and has documents**
```bash
# Replace INDEX_NAME with each of the 3 index names
curl -X GET \
  "https://sdlc-test-ai-search.search.windows.net/indexes/ras-helper-index-v1/stats?api-version=2023-11-01" \
  -H "api-key: <AZURE_SEARCH_ADMIN_KEY>"

# Expected: {"documentCount": N, "storageSize": N}
# documentCount == 0  means the index is empty → agents will run but produce generic output
```

**Option B — Python**
```python
import os, requests
from dotenv import load_dotenv
load_dotenv()

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
indexes = ["ras-helper-index-v1", "tcg-manual-index-v1", "tcg-cucumber-index-v1"]

for idx in indexes:
    r = requests.get(
        f"{endpoint}/indexes/{idx}/stats?api-version=2023-11-01",
        headers={"api-key": key}
    )
    if r.status_code == 200:
        stats = r.json()
        print(f"{idx}: {stats['documentCount']} docs, {stats['storageSize']} bytes")
    else:
        print(f"{idx}: MISSING or ERROR — {r.status_code} {r.text}")
```

**Step 3 — Check semantic configuration exists** (required by the code's `query_type="semantic"`)
```bash
curl -X GET \
  "https://sdlc-test-ai-search.search.windows.net/indexes/ras-helper-index-v1?api-version=2023-11-01" \
  -H "api-key: <AZURE_SEARCH_ADMIN_KEY>" | python -m json.tool | grep -A5 "semanticConfigurations"

# Expected: "semanticConfigurations": [{"name": "default", ...}]
# If missing: DocIngestionFunction creates it when it creates the index
```

### What a passing result looks like
```
ras-helper-index-v1:      142 docs
tcg-manual-index-v1:       87 docs
tcg-cucumber-index-v1:     54 docs
```

### Common failure causes
| Issue | Cause | Fix |
|-------|-------|-----|
| 401 | Wrong admin key | Azure Portal → AI Search → Keys → Primary Admin Key |
| Index missing | Never ran DocIngestionFunction | Run it with a CSV (see `05_deployment.md`) |
| 0 documents | Index exists but not seeded | Run DocIngestionFunction with data CSV |
| Semantic config missing | Index created outside DocIngestionFunction | Delete and recreate via DocIngestionFunction |

---

## 3. Azure PostgreSQL

### What the code needs
- Host: `sdlc-test.postgres.database.azure.com`, DB: `postgres`
- SSL required (`sslmode='require'` in code)
- 3 tables: `agent_prompts`, `user_request_logs`, `user_feedback`
- The `agent_prompts` table can be empty (system falls back to hardcoded prompts) **except** for `("TCG", "team_prompt")` row — if that's missing, `ExecuteTCG` crashes on cold start (Bug 1)

### How to verify

**Option A — psql CLI**
```bash
# Test connection
psql "host=sdlc-test.postgres.database.azure.com port=5432 dbname=postgres user=<user> password=<pass> sslmode=require" \
  -c "\dt"

# Expected: list of tables including agent_prompts, user_request_logs, user_feedback
# "connection refused" = firewall blocking your IP
# "password auth failed" = wrong credentials
```

**Check tables exist**
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- Expected: agent_prompts, user_feedback, user_request_logs
```

**Check for the critical TCG team_prompt row**
```sql
SELECT id, ai_helper_name, agent_name, version
FROM agent_prompts
WHERE ai_helper_name = 'TCG' AND agent_name = 'team_prompt';
-- If 0 rows returned → ExecuteTCG will crash at cold start
```

**Option B — Python**
```python
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        sslmode="require"
    )
    cur = conn.cursor()

    # Check tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = [r[0] for r in cur.fetchall()]
    for t in ["agent_prompts", "user_request_logs", "user_feedback"]:
        status = "OK" if t in tables else "MISSING — run DDL from 05_deployment.md"
        print(f"  {t}: {status}")

    # Check critical TCG prompt row
    cur.execute("SELECT COUNT(*) FROM agent_prompts WHERE ai_helper_name='TCG' AND agent_name='team_prompt'")
    count = cur.fetchone()[0]
    print(f"  TCG team_prompt row: {'OK' if count else 'MISSING — ExecuteTCG will crash'}")

    conn.close()
    print("PostgreSQL: connection OK")
except Exception as e:
    print(f"PostgreSQL: FAILED — {e}")
```

### What a passing result looks like
```
agent_prompts:     OK
user_request_logs: OK
user_feedback:     OK
TCG team_prompt:   OK  (or acceptable if you patched the cold-start bug)
PostgreSQL:        connection OK
```

### Common failure causes
| Issue | Cause | Fix |
|-------|-------|-----|
| Connection refused | Azure firewall blocking your IP | Azure Portal → PostgreSQL → Networking → Add your IP |
| Password auth failed | Wrong `POSTGRES_USER` / `POSTGRES_PASSWORD` | Check `.env` against Portal → PostgreSQL → Connection strings |
| SSL required error | `sslmode` not set | Code already sets `sslmode='require'` — make sure you're not overriding it |
| Tables missing | Schema never created | Run DDL from `05_deployment.md` |

---

## 4. Azure Blob Storage

### What the code needs
- Account: `sdlctest`
- A container to upload CSV files into (name is set by whoever calls `DocIngestionFunction`)
- Account key in `STORAGE_ACCOUNT_KEY`

### How to verify

**Option A — Azure CLI**
```bash
az storage container list \
  --account-name sdlctest \
  --account-key <STORAGE_ACCOUNT_KEY> \
  --output table

# Expected: list of containers
# AuthenticationFailed = wrong key
```

**Option B — Python**
```python
import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
load_dotenv()

account_name = os.getenv("STORAGE_ACCOUNT_NAME")
account_key = os.getenv("STORAGE_ACCOUNT_KEY")

try:
    client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key
    )
    containers = [c["name"] for c in client.list_containers()]
    print(f"Blob Storage: OK — containers: {containers}")
except Exception as e:
    print(f"Blob Storage: FAILED — {e}")
```

### What a passing result looks like
```
Blob Storage: OK — containers: ['csv-uploads', ...]
```

### Common failure causes
| Issue | Cause | Fix |
|-------|-------|-----|
| AuthenticationFailed | Wrong `STORAGE_ACCOUNT_KEY` | Portal → Storage Account → Access keys → key1 |
| ResourceNotFound | Wrong `STORAGE_ACCOUNT_NAME` | Check account name in Portal |
| No containers listed | Container not created | Create it via Portal or `az storage container create` |

---

## 5. Jira

This is the most complex external dependency. It has two sub-systems the code relies on:
**Jira Core REST API** (user auth, fetch/update issues) and **Xray REST API** (create Test issues with steps).

### What the code needs

| Requirement | Why |
|-------------|-----|
| Valid Jira account (username + password/API token) | All API calls use Basic Auth |
| `BROWSE_PROJECTS` permission | To search and fetch issues |
| `EDIT_ISSUES` permission | RAS push — update story summary/description |
| `CREATE_ISSUES` permission on the target project | TCG push — create Test issues |
| `LINK_ISSUES` permission | TCG push — link Test → Story |
| Issue type `Test` exists in the project | TCG push — `create_issue()` hardcodes `issuetype: "Test"` |
| `customfield_12077` — Acceptance Criteria field | RAS input — reading ACs from stories |
| `customfield_10125` — Test Type field (Xray) | TCG push — set Manual/Cucumber type |
| `customfield_10127` — Cucumber Steps field (Xray) | TCG push — set cucumber scenario |
| Xray plugin installed | TCG push — Xray endpoints at `/rest/raven/1.0/` |
| `Tests` issue link type exists | TCG push — linking test to parent story |

> **Note on auth:** The frontend uses **Basic Auth** (username:password base64) for `authenticate_user()`, `get_accessible_issues()`, and `update_jira_issue()`. However, `create_issue()`, `add_test_step_manual()`, `link_issues()` use the **session cookie path** (`execute_jira_request_until_sucess`). This means for TCG push to work, `JiraClient.login()` must have been called to populate `self.cookies`. If only `set_credentials()` was called, those methods will return the default "Not logged in" error silently.

### How to verify

**Step 1 — Test basic auth and connectivity**
```bash
# Replace with your Jira base URL and credentials
JIRA_URL="https://jira-yourcompany.com.au"
USER="your.email@company.com"
PASS="your-password-or-api-token"

curl -u "$USER:$PASS" "$JIRA_URL/rest/api/2/myself"
# Expected: 200 with {"displayName":"...","emailAddress":"..."}
# 401 = wrong credentials   |   404 = wrong base URL
```

**Step 2 — Check permissions on your user**
```bash
curl -u "$USER:$PASS" \
  "$JIRA_URL/rest/api/2/mypermissions?projectKey=<PROJ_KEY>&permissions=BROWSE_PROJECTS,EDIT_ISSUES,CREATE_ISSUES,LINK_ISSUES"

# Expected: each permission has "havePermission": true
```

**Step 3 — Verify the Acceptance Criteria custom field exists**
```bash
curl -u "$USER:$PASS" "$JIRA_URL/rest/api/2/field" | python -m json.tool | grep -A2 "12077"
# or search by name:
curl -u "$USER:$PASS" "$JIRA_URL/rest/api/2/field" | python -c "
import json,sys
fields = json.load(sys.stdin)
ac = [f for f in fields if 'acceptance' in f.get('name','').lower() or f.get('id') == 'customfield_12077']
print(ac)
"
# Expected: field with id 'customfield_12077' and name containing 'Acceptance'
# If missing: the field ID is wrong for this Jira instance — find the correct ID and update jira_client.py
```

**Step 4 — Verify Xray is installed**
```bash
curl -u "$USER:$PASS" "$JIRA_URL/rest/raven/1.0/api/test/PROJ-1/step"
# Expected: 200 or 404 (issue not found) — NOT a 404 on the path itself
# If you get "No content found" or "endpoint not found" at the /rest/raven/ path: Xray is not installed
```

**Step 5 — Verify Xray custom fields exist**
```bash
# Check Test Type field (customfield_10125)
curl -u "$USER:$PASS" "$JIRA_URL/rest/api/2/field" | python -c "
import json,sys
fields = json.load(sys.stdin)
xray = [f for f in fields if f.get('id') in ('customfield_10125','customfield_10127')]
for f in xray: print(f['id'], f['name'])
"
# Expected:
#   customfield_10125  Test Type  (or similar Xray field name)
#   customfield_10127  Cucumber Test  (or similar)
# If different IDs: update the hardcoded values in jira_client.py
```

**Step 6 — Verify "Tests" issue link type exists**
```bash
curl -u "$USER:$PASS" "$JIRA_URL/rest/api/2/issueLinkType"
# Expected: {"issueLinkTypes":[..., {"name":"Tests",...},...]}
# If "Tests" is not in the list: TCG link step will fail with 400
```

**Step 7 — Verify the Test issue type exists in your project**
```bash
curl -u "$USER:$PASS" "$JIRA_URL/rest/api/2/project/<PROJ_KEY>/statuses"
# or:
curl -u "$USER:$PASS" "$JIRA_URL/rest/api/2/issue/createmeta?projectKeys=<PROJ_KEY>&expand=projects.issuetypes" \
  | python -c "
import json,sys
meta = json.load(sys.stdin)
types = [t['name'] for p in meta['projects'] for t in p['issuetypes']]
print('Issue types:', types)
print('Test type present:', 'Test' in types)
"
```

**Step 8 — Full integration smoke test (Python)**
```python
import os, base64, requests
from dotenv import load_dotenv
load_dotenv()

base_url = os.getenv("JIRA_ENDPOINT", "").rstrip("/")
user = input("Jira username: ")
pwd  = input("Jira password: ")
auth = base64.b64encode(f"{user}:{pwd}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

checks = {
    "Auth (myself)":      f"{base_url}/rest/api/2/myself",
    "Issue search":       f"{base_url}/rest/api/2/search?jql=issuetype=Story&maxResults=1",
    "Field list":         f"{base_url}/rest/api/2/field",
    "Xray endpoint":      f"{base_url}/rest/raven/1.0/api/test",
    "Link types":         f"{base_url}/rest/api/2/issueLinkType",
}

for name, url in checks.items():
    r = requests.get(url, headers=headers, verify=False)
    print(f"  {name}: {r.status_code} {'OK' if r.status_code == 200 else 'CHECK NEEDED'}")
```

### What a passing result looks like
```
  Auth (myself):    200 OK
  Issue search:     200 OK
  Field list:       200 OK
  Xray endpoint:    200 OK
  Link types:       200 OK
```

### Common failure causes
| Issue | Cause | Fix |
|-------|-------|-----|
| 401 on all calls | Wrong credentials | Use Jira API token (not LDAP password) if on Jira Cloud |
| `customfield_12077` returns nothing | Wrong field ID for this instance | Run field list check, find the AC field, update `jira_client.py` |
| Xray 404 on `/rest/raven/` path | Xray plugin not installed | Contact Jira admin to install Xray |
| `Test` not in issue types | Project doesn't have Test type | Contact Jira admin to add Test issue type to project scheme |
| `Tests` link type missing | Link type not configured | Contact Jira admin to add "Tests" issue link type |
| TCG push silently fails | `self.cookies` is None — `login()` never called | This is a code-level issue — `create_issue()` checks cookies, not Basic Auth. Call `jira.login()` before any TCG push. |

---

## 6. Azure Function App

### What the code needs
- App: `func-mortgage-dev`
- Python 3.11 runtime
- Durable Functions extension bundle `[4.*, 5.0.0)`
- All env vars from `.env` set as Application Settings
- GitHub secret `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` for CI/CD

### How to verify

**Step 1 — Check the Function App is running**
```bash
curl https://func-mortgage-dev.azurewebsites.net/api/health
# or just:
curl https://func-mortgage-dev.azurewebsites.net
# Expected: any response (not connection refused)
```

**Step 2 — Trigger a test orchestration**
```bash
curl -X POST \
  "https://func-mortgage-dev.azurewebsites.net/api/DurableFunctionsOrchestrator" \
  -H "Content-Type: application/json" \
  -d '{"helper_name":"RAS","requirement":"test","input_type":"text_input"}'

# Expected: 202 with body containing "statusQueryGetUri"
# 500 = environment variables missing or function crashed
```

**Step 3 — Check Application Settings in Azure Portal**

Portal → Function App `func-mortgage-dev` → Configuration → Application Settings

Confirm these keys are present (values should not be empty):
```
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_ADMIN_KEY
STORAGE_ACCOUNT_NAME
STORAGE_ACCOUNT_KEY
AZURE_CHAT_MODEL_NAME
AZURE_OPENAI_API_VERSION
AZURE_MODEL_DEPLOYMENT_NAME
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_TEMPERATURE
AZURE_EMBEDDING
AZURE_OPENAI_API_KEY
```

**Step 4 — Check the CI/CD secret exists**

GitHub → repo → Settings → Secrets → `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` should be listed.

---

## Full Pre-Flight Checklist

Run this before going live or debugging any integration issue:

```
AZURE OPENAI
  [ ] GPT-4o deployment responds to chat completions call → HTTP 200
  [ ] ada-002 deployment returns 1536-dim embedding vector

AZURE AI SEARCH
  [ ] Service reachable with admin key → HTTP 200
  [ ] ras-helper-index-v1 exists, documentCount > 0
  [ ] tcg-manual-index-v1 exists, documentCount > 0
  [ ] tcg-cucumber-index-v1 exists, documentCount > 0
  [ ] All 3 indexes have "default" semantic configuration

AZURE POSTGRESQL
  [ ] Can connect from your machine (firewall allows your IP)
  [ ] Tables: agent_prompts, user_request_logs, user_feedback all exist
  [ ] agent_prompts has row for ('TCG', 'team_prompt') OR Bug 1 is patched

AZURE BLOB STORAGE
  [ ] Account reachable with storage key
  [ ] At least one container exists for CSV uploads

JIRA
  [ ] Auth (GET /rest/api/2/myself) → HTTP 200
  [ ] User has BROWSE_PROJECTS, EDIT_ISSUES, CREATE_ISSUES, LINK_ISSUES
  [ ] customfield_12077 is the Acceptance Criteria field (verify field ID)
  [ ] customfield_10125 is the Xray Test Type field (verify field ID)
  [ ] customfield_10127 is the Xray Cucumber field (verify field ID)
  [ ] Issue type "Test" exists in target project
  [ ] "Tests" issue link type exists
  [ ] Xray plugin installed: /rest/raven/1.0/ returns 200 not path-404

AZURE FUNCTION APP
  [ ] App is running (not stopped)
  [ ] All env vars set as Application Settings
  [ ] POST to orchestrator endpoint returns 202
  [ ] GitHub secret AZURE_FUNCTIONAPP_PUBLISH_PROFILE is present
```

---

## Finding Jira Custom Field IDs for a Different Instance

The field IDs `customfield_12077`, `customfield_10125`, `customfield_10127` are specific to the original Jira instance. If deploying to a different Jira, find the correct IDs like this:

```bash
# Dump all fields and search
curl -u "user:pass" "https://your-jira.com/rest/api/2/field" \
  | python -c "
import json, sys
fields = json.load(sys.stdin)
# Print all custom fields with their IDs and names
for f in fields:
    if f['id'].startswith('customfield_'):
        print(f['id'].ljust(30), f['name'])
" | sort

# Look for:
#   Acceptance Criteria   → note the ID, update fetch_issue_details() in jira_client.py
#   Test Type (Xray)      → note the ID, update create_issue() payload
#   Cucumber Test (Xray)  → note the ID, update add_test_cucumber() payload
```

Then update these three locations in `backend/common/jira/jira_client.py`:
- `create_issue()` line ~383: `"customfield_10125"`
- `add_test_cucumber()` line ~426: `"customfield_10127"`

And in the frontend `fetch_issue_details()`:
- `frontend/src/services/jira_client.py`: wherever `customfield_12077` is read
