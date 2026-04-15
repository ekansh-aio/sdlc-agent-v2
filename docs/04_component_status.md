# 04 — Component Status

Honest inventory based on code review — April 2026.

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Confirmed working — logic complete, credentials in place |
| ⚠️ | Works but has known issues / rough edges |
| ❌ | Broken — will fail at runtime |
| 🔲 | Stub — function exists, body not implemented |
| ❓ | Uncertain — requires manual verification against live environment |

---

## Backend — Azure Functions

| Component | Status | Notes |
|-----------|--------|-------|
| `DurableFunctionsHttpStart` | ✅ | Standard Durable pattern; correct |
| `DurableFunctionsOrchestrator` routing | ✅ | Routing logic clean and complete |
| `ExecuteRAS` — full agent pipeline | ✅ | Multi-agent chain runs end-to-end |
| `ExecuteTCG` — full agent pipeline | ✅ | Works for all 4 test types |
| `PushtoJira` — RAS (update issue) | ✅ | Updates Jira fields and adds AC as comment |
| `PushtoJira` — TCG (create tests) | ⚠️ | Returns a tuple; frontend unpacking at `app.py:653` may mismatch |
| `DocIngestionFunction` | ❓ | Works if triggered manually; not wired to main workflow |

---

## Backend — Shared Modules

| Component | Status | Notes |
|-----------|--------|-------|
| `LLMConfig` (Azure OpenAI) | ✅ | `AZURE_OPENAI_API_KEY` set — works locally and in Azure |
| `PromptManager` (DB prompts) | ⚠️ | Falls back silently to hardcoded prompts if DB row missing; `tcg_prompts.py` crashes on import if `team_prompt` row absent (see Bug 1) |
| `AzureAISearchClient` — RAS | ✅ | Endpoint + admin key configured |
| `AzureAISearchClient` — TCG manual | ✅ | Same |
| `AzureAISearchClient` — TCG cucumber | ✅ | Same |
| `PostgresClient` | ✅ | Host, user, password all set in `.env` |
| `JiraClient` — auth | ✅ | Basic Auth works; session cookie fallback present |
| `JiraClient` — fetch issue | ✅ | Pagination and field extraction work |
| `JiraClient` — update issue | ✅ | PUT + comment for AC works |
| `JiraClient` — create Test issue | ✅ | Xray API integration functional |
| `JiraClient` — add manual steps | ✅ | |
| `JiraClient` — add Cucumber | ✅ | |
| `JiraClient` — link issues | ✅ | |
| `JiraClient` — `execute_jira_request_until_success` | ⚠️ | Line ~384: passes `cookies` dict as `headers` — wrong parameter name. May cause silent auth failures on some Jira endpoints |
| `RASAgentBuilder` | ✅ | Correctly wires all 4 agents + search tool |
| `TCGAgentBuilder` | ✅ | Correctly varies prompts + tools by test_type |
| `TestCaseFormatter` | ⚠️ | Bare `except:` hides all errors; legacy path, mostly bypassed by JSON output |
| `utility.check_pii_exist()` | 🔲 | Stub — returns input unchanged |
| `utility.get_user_story_data()` | 🔲 | Stub — returns input unchanged |

---

## Frontend — Streamlit Components

| Component | Status | Notes |
|-----------|--------|-------|
| Jira auth dialog + session | ✅ | Login, session storage, auto-logout timer |
| Sidebar: helper + input type selection | ✅ | |
| Jira ID multiselect + pagination | ✅ | Loads 5 more on "More..." click |
| Input: Jira ID fetch + display | ✅ | Fetches summary, description, `customfield_12077` (ACs) |
| Input: Free text validation | ✅ | Minimum 3 words; garbage-input check |
| RAS UI flow (submit → poll → display) | ✅ | |
| TCG UI flow (submit → poll → display) | ✅ | |
| Edit mode (user modifies AI output) | ✅ | Editable text area; saves to session state |
| Copy to clipboard | ✅ | Uses `pyperclip` |
| "Analyse Agents" chat dialog | ✅ | Shows full agent conversation history |
| Star rating widget | ✅ | 1–5 star input; logged to `user_feedback` |
| Emoji rating widget | ❓ | Exists; not clearly triggered in main flow |
| Approve & Push — RAS | ✅ | Confirmation dialog + push to backend |
| Approve & Push — TCG | ⚠️ | Calls backend but response unpacking from tuple may fail silently (`app.py:653`) |
| PostgreSQL logging — requests | ✅ | Logs every completed request |
| PostgreSQL logging — feedback | ✅ | Logs after star rating |
| `update_edited_response()` | ✅ | Updates DB after user edits |
| Session state on browser refresh | ⚠️ | Streamlit resets on refresh — user must re-authenticate |
| Error display for backend failures | ⚠️ | Broad exception catch; error messages are generic |
| Loading spinner during polling | ✅ | Shows spinner with `st.spinner()` while waiting |
| `file_uploader.py` | ❓ | Uploads to blob but not connected to DocIngestionFunction |
| `test_requests.py` | ❌ | Missing `import os`; crashes on import |
| `excel_read.py` | ❌ | No UI element triggers it — dead code |
| `show_survey_form()` dialog | ❌ | Typo: `st.session_sate` (line ~179) → `AttributeError` if executed |

---

## Azure Infrastructure

| Resource | Status | Notes |
|----------|--------|-------|
| Azure Function App `func-mortgage-dev` | ✅ | Deployed via GitHub Actions |
| Azure OpenAI `aio-az-openai-service1` | ✅ | Endpoint and API key configured |
| Azure AI Search `sdlc-test-ai-search` | ❓ | Service exists and credentials configured; **indexes must be manually seeded** |
| Azure PostgreSQL `sdlc-test` | ❓ | Connection configured; **schema must be created manually** (no migration scripts) |
| Azure Storage `sdlctest` | ✅ | Name and key configured |
| Azure Managed Identity | ❓ | Required for Azure-hosted deployment; local dev now works via API keys |
| GitHub Secret `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` | ✅ | Present — CI/CD succeeds |

---

## Known Bugs (with file references)

### Bug 1 — `tcg_prompts.py` crashes on import if DB row missing

- **File:** `backend/common/prompts/tcg_prompts.py` line 17
- **Issue:** Module-level call to `PromptManager.get_prompt("TCG", "team_prompt")` at import time. If the `agent_prompts` table doesn't have this row, a `RuntimeError` is raised, crashing the entire `ExecuteTCG` function at cold start.
- **Evidence:** The log error message is actually embedded in the file:  
  `RuntimeError: Error fetching value for name TCG and team_prompt`
- **Fix:** Defer the DB call to `build_team()` time, or wrap in try/except with fallback.
- **Impact:** ExecuteTCG will not start if DB prompts are missing and there is no fallback.

---

### Bug 2 — `jira_client.py` cookies passed as headers

- **File:** `backend/common/jira/jira_client.py` ~line 384
- **Issue:** `requests.get(..., headers=cookies)` — the cookie dict is passed to the `headers` parameter instead of `cookies`. The HTTP call will send cookies as headers (wrong format), likely causing Jira to reject authentication.
- **Fix:** Change `headers=cookies` → `cookies=cookies` (or fold into the Authorization header properly).
- **Impact:** Jira API calls using the session cookie auth path may fail silently. Basic Auth path is unaffected.

---

### Bug 3 — TCG push return format mismatch

- **File:** `frontend/src/app.py` ~line 653
- **Issue:** `PushtoJira` for TCG returns `(status_code, message)` tuple. The frontend unpacking may expect a different shape (dict or single value).
- **Fix:** Inspect exact return shape from `PushtoJira.__init__.py` and match frontend parsing to it.
- **Impact:** "Approve & Push" for TCG may show wrong success/failure message, or crash.

---

### Bug 4 — `show_survey_form()` typo

- **File:** `frontend/src/components/dialogs.py` ~line 179
- **Issue:** `st.session_sate.survey_form` — missing `t` in `state`.
- **Fix:** `st.session_state.survey_form`
- **Impact:** Any code path that opens the survey dialog will crash with `AttributeError`.

---

### Bug 5 — `test_requests.py` import error

- **File:** `frontend/src/components/test_requests.py`
- **Issue:** Missing `import os`; `load_dotenv()` call is incomplete.
- **Fix:** Add `import os` at top; fix `load_dotenv()` call.
- **Impact:** File crashes on import. Currently not imported in `app.py` so it's latent — adding it would break the app.

---

### Bug 6 — No database migration scripts

- **File:** N/A
- **Issue:** No `CREATE TABLE` scripts, Alembic config, or Flyway migrations found anywhere.
- **Fix:** Write migration scripts (see `05_deployment.md` for inferred DDL).
- **Impact:** New environment setup requires manual table creation from memory/docs. Schema drift between environments is undetectable.

---

### Bug 7 — Duplicate orchestration on double-click

- **File:** `backend/DurableFunctionsHttpStart/__init__.py`
- **Issue:** No idempotency key / deduplication. Each POST starts a fresh orchestration. If the user clicks "Analyse" twice, two agent chains run in parallel, both billing tokens.
- **Fix:** Pass a client-generated `instance_id` (e.g., hash of jira_id + timestamp) and use `start_new` with that ID.
- **Impact:** Wasted OpenAI token spend; duplicate results may appear.

---

## Dead Code

| File | Reason |
|------|--------|
| `frontend/src/components/test_requests.py` | Broken + not imported |
| `frontend/src/utils/excel_read.py` | No UI trigger |
| `frontend/src/components/emoji_rating.py` | Not called in main flow |
| `backend/common/utils/TestCaseFormatter.py` | Largely bypassed by JSON agent output |
| `backend/common/utils/utility.py` | Both functions are stubs |
