# 07 — V2 Roadmap

What to build next, what debt to pay first, and the architectural improvements that will unlock scale.

---

## Priority 1 — Fix Before Building Anything New (Critical Debt)

These are bugs or gaps that will bite you in production. Fix them before adding features.

---

### P1-A: Add database migration tooling

**Why urgent:** Any schema change you make in V2 will cause silent drift between environments. Without migration scripts, a new team member setting up a dev environment has to guess the schema.

**What to do:**
1. Install Alembic: `pip install alembic`
2. Write `env.py` pointing at your PostgreSQL
3. Write the initial migration: `alembic revision --autogenerate -m "initial_schema"`
4. Commit `alembic/` alongside your code
5. Add `alembic upgrade head` to your deployment pipeline

---

### P1-B: Fix `tcg_prompts.py` module-level DB call

**Why urgent:** If the `agent_prompts` table is empty on a fresh environment, `ExecuteTCG` crashes at cold start with a `RuntimeError`. Anyone deploying to a new environment will hit this.

**File:** `backend/common/prompts/tcg_prompts.py` line 17

**Fix:**
```python
# Instead of calling DB at module level:
try:
    TEAM_PROMPT = PromptManager().get_prompt("TCG", "team_prompt")
except Exception:
    TEAM_PROMPT = TEAM_PROMPT_FALLBACK   # use hardcoded constant
```

---

### P1-C: Fix Jira client `cookies-as-headers` bug

**File:** `backend/common/jira/jira_client.py` ~line 384

**Fix:** Change `headers=cookies` → `cookies=cookies` in the requests call.

This is a silent bug — Jira may accept the malformed request on some endpoints but not others.

---

### P1-D: Fix TCG push return value mismatch

**Files:** `backend/PushtoJira/__init__.py`, `frontend/src/app.py` ~line 653

Confirm the exact shape returned by `PushtoJira` for the TCG path and update the frontend parsing to match. Add explicit error handling so a push failure shows a useful message instead of a silent wrong-success.

---

### P1-E: Fix `show_survey_form()` typo

**File:** `frontend/src/components/dialogs.py` ~line 179

Change `st.session_sate` → `st.session_state`. One character fix.

---

## Priority 2 — Architectural Improvements (Enable Scale and Reliability)

---

### P2-A: Add idempotency to orchestration starts

**Problem:** Double-clicking "Analyse" starts two parallel agent chains — double the token spend, duplicate results.

**Fix:** Generate a deterministic `instance_id` on the frontend (e.g., SHA256 of `jira_id + user + timestamp rounded to 5s`) and pass it to `start_new()`. Durable Functions will reject a duplicate start with the same instance ID.

---

### P2-B: Implement automated index refresh

**Problem:** The AI Search indexes are seeded once manually. As new stories and test cases are created in Jira, the RAG context gets stale — the agents will keep citing old examples.

**Options (pick one):**
1. **Scheduled batch job:** A nightly Azure Function that queries Jira for all Stories closed in the last 7 days, generates embeddings, and upserts into the index.
2. **Jira webhook trigger:** On issue transition to "Done", fire a webhook to a lightweight Azure Function that indexes that single issue.

Option 2 is real-time but requires Jira webhook configuration. Option 1 is simpler to implement.

---

### P2-C: Externalize Jira custom field IDs

**Problem:** `customfield_12077`, `customfield_10125`, `customfield_10127` are hardcoded throughout the codebase. Any other Jira instance will have different IDs.

**Fix:** Add to `.env`:
```bash
JIRA_FIELD_AC=customfield_12077
JIRA_FIELD_TEST_TYPE=customfield_10125
JIRA_FIELD_CUCUMBER=customfield_10127
```
Read these via `os.getenv()` in `jira_client.py` instead of hardcoding.

---

### P2-D: Seed `agent_prompts` table via migration

**Problem:** The system silently uses hardcoded fallback prompts. There's no record of which prompt version is running in production.

**Fix:** Add a seed migration that inserts the current hardcoded prompts as version 1 into the DB. Then the DB is always the source of truth and the fallback code can be removed or limited to a safety net only.

---

### P2-E: Add observability

**Minimum viable monitoring:**
1. Azure Application Insights integration on the Function App (one config line)
2. Alert on: Function failure rate > 5%, P95 duration > 5 minutes
3. A simple Grafana or Power BI dashboard over `user_request_logs`: requests per day, average duration, error rate, rating distribution

---

## Priority 3 — Feature Work (V2 Scope)

---

### V2-01: Streamlit → React/Next.js frontend

**Why:** Streamlit has hard limitations:
- Session state is wiped on refresh
- Cannot run UI operations in background (polling blocks the thread)
- No persistent login (no cookies/JWT)
- Difficult to build rich multi-column layouts

**Recommended path:** Replace Streamlit with a Next.js frontend that calls the Azure Functions directly. Keep the backend unchanged. Use Azure AD B2C or Jira OAuth for login instead of credential pass-through.

**Impact:** High effort (full frontend rewrite) but removes all the Streamlit UX rough edges.

---

### V2-02: Persistent login with Jira OAuth

**Why:** Currently every browser refresh requires re-entering Jira credentials. This is a significant UX problem for power users.

**Fix:** Implement Jira OAuth 2.0 flow. Store the OAuth token in a browser cookie (httpOnly). Token refresh in the background. This requires a frontend that supports redirects (i.e., React/Next.js, not Streamlit).

---

### V2-03: Automated index update (see P2-B)

Operationalize the ingestion pipeline so the RAG context stays current without manual intervention.

---

### V2-04: TCG — support for additional test types

**Current:** Manual steps and Cucumber BDD.

**Add:**
- API test case generation (Postman/Newman format)
- Performance test scenario generation (JMeter, k6)

Both would be new `AnalyserAgent` prompt variants and new Jira push paths.

---

### V2-05: Batch processing

**Why:** QE leads often need to generate test cases for an entire epic (10–20 stories) at once. The current UI is one-story-at-a-time.

**Design:**
- Accept a list of Jira IDs in one submission
- Fan out to parallel Durable orchestrations (one per story)
- Aggregate results in a review UI
- Bulk push to Jira with one confirmation

---

### V2-06: Test case de-duplication

**Problem:** If the same story is processed twice, duplicate test cases will be pushed to Jira.

**Fix:** Before creating a new Test issue, query Jira for existing Test issues linked to the parent. If one with the same summary exists, update instead of create.

---

### V2-07: Prompt A/B testing infrastructure

**Foundation is already in place:** The `agent_prompts` table has a `version` column and the system reads the highest version. 

**What's missing:** A mechanism to:
1. Flag a prompt version as "experiment"
2. Route a percentage of requests to the experimental version
3. Compare output quality (via star ratings) between versions

This would let the team tune prompts safely without a full rollout.

---

### V2-08: Implement PII detection (`utility.py` stubs)

**Files:** `backend/common/utils/utility.py`

`check_pii_exist()` and `get_user_story_data()` are stubs that return input unchanged. For a production system handling real customer stories, PII detection should scan the input before it is sent to Azure OpenAI and either redact or warn the user.

**Recommended approach:** Azure AI Language Service has a built-in PII entity recognition endpoint. Call it before handing content to the agent chain.

---

## Technical Debt Summary

| Debt item | Effort | Risk if ignored |
|-----------|--------|----------------|
| No DB migrations | Low | Schema drift, painful V2 deploys |
| `tcg_prompts.py` cold-start crash | Low | ExecuteTCG broken on fresh environments |
| Jira cookies-as-headers | Low | Silent auth failures on some Jira endpoints |
| TCG push return mismatch | Low | Silent push failures for TCG |
| Survey form typo | Trivial | Crash if survey is triggered |
| No automated tests | High | Any refactor risks silent regressions |
| Hardcoded Jira field IDs | Low | Non-portable to other Jira instances |
| No idempotency on orchestration | Medium | Double billing on double-click |
| Stale AI Search indexes | Medium | Degrading output quality over time |
| Streamlit session wipe on refresh | High (full rewrite) | Poor UX for all users, every day |
| No PII detection | Medium | Compliance risk if real customer data is processed |
| Dead code (`test_requests.py`, `excel_read.py`) | Trivial | Confusion for new developers |

---

## Recommended V2 Sequence

```
Sprint 1 (stabilization):
  P1-A  DB migrations
  P1-B  tcg_prompts cold-start fix
  P1-C  Jira cookies fix
  P1-D  TCG push return fix
  P1-E  Survey typo fix
  P2-D  Seed agent_prompts via migration
  P2-E  Add Application Insights

Sprint 2 (reliability):
  P2-A  Idempotent orchestration
  P2-C  Externalize Jira field IDs
  V2-06 Test case de-duplication
  V2-08 PII detection stub → real implementation

Sprint 3 (UX + scale):
  P2-B  Automated index refresh
  V2-05 Batch processing (epic-level TCG)
  V2-02 Jira OAuth (if React frontend ready)

Sprint 4+ (platform evolution):
  V2-01 React/Next.js frontend
  V2-04 Additional test types
  V2-07 Prompt A/B testing
```
