# 06 — Software Requirements Specification (SRS)

Reconstructed from code review. This documents what the system actually does, not what was originally intended.

---

## 1. Purpose

The SDLC Agents system provides QE (Quality Engineering) teams with an AI assistant that:
1. **Rewrites vague requirements** into structured, INVEST-compliant user stories
2. **Generates test cases** (manual step-by-step or Cucumber BDD) from user stories
3. **Pushes results directly into Jira** as updated story fields or new Xray Test issues

The target users are QE engineers and business analysts who work daily in Jira and want AI assistance without leaving their workflow.

---

## 2. Users and Roles

| Role | Description | How they use the system |
|------|-------------|------------------------|
| QE Engineer | Quality engineer with Jira access | Generates test cases from Jira stories; reviews and pushes to Jira |
| Business Analyst | Analyst writing requirements | Uses RAS to refine raw requirements into user stories |
| Admin (implicit) | Whoever manages Azure resources | Seeds AI Search indexes; manages DB prompts |

Authentication is **Jira credential-based** — no separate user accounts. Any user with a valid Jira login can access the tool.

---

## 3. Functional Requirements

### FR-01: Jira Authentication

- The system shall authenticate users using their Jira username and password
- Authentication shall call `GET /rest/api/2/myself` to validate credentials
- Credentials shall be stored in Streamlit session state (in-memory only, not persisted)
- Sessions shall remain active for the browser session duration; a browser refresh requires re-authentication

### FR-02: Requirement Input

- The system shall accept requirements via two input modes:
  - **Free Text:** User pastes or types raw requirement text (minimum 3 words; garbage input rejected)
  - **Jira ID:** User selects from a list of their accessible Jira issues (Story type by default)
- For Jira ID input, the system shall fetch the issue's `summary`, `description`, and `customfield_12077` (acceptance criteria)
- The system shall display fetched Jira issue details to the user before submission

### FR-03: RAS — Requirement Analysis & Standardization

- The system shall rewrite a given requirement into a user story containing:
  - **Title:** Concise, descriptive
  - **Description:** "As a [persona], I want [action], so that [value]" format
  - **Acceptance Criteria:** 2–4 criteria in Given-When-Then format
  - **Priority:** High / Medium / Low
- The story shall conform to INVEST principles (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- The system shall use a 4-agent chain (Request → Analyse → Review → Format) with reviewer feedback loop
- For Jira ID inputs, the system shall augment the agent context with semantically similar historical requirements from Azure AI Search (top 3, score ≥ 0.85)

### FR-04: TCG — Test Case Generation

- The system shall generate test cases in two formats:
  - **Manual:** Structured step-by-step tests with Action, Data, and Expected Result per step
  - **Cucumber / Automated:** BDD scenarios with Given-When-Then syntax
- Each test case shall include: TestCaseID, Summary, Description, Priority (risk-based), and steps
- TestCaseID format: `<parent_jira_id> - TC <nn>` (e.g., `AIHQE-300 - TC 01`)
- The system shall use semantic search to retrieve similar historical test cases when input is a Jira ID
- The system shall generate multiple test cases per request (typically 3–5)

### FR-05: Result Review and Edit

- The system shall display the AI-generated output to the user before any Jira action
- The user shall be able to edit the output in a text area
- The system shall preserve the edited version for push to Jira
- The system shall record whether the user edited the response in the audit log

### FR-06: Approve & Push to Jira

- **RAS push:** The system shall update the Jira story's title, description, and add acceptance criteria as a comment
- **TCG push:** The system shall, for each generated test case:
  1. Create a new Jira issue of type "Test" in the specified project
  2. Add all test steps (manual) or the cucumber scenario (automated) to the test issue
  3. Link the test issue to the parent story with a "Tests" link
- The user shall confirm before any Jira write operation

### FR-07: Chat History / Agent Transparency

- The system shall provide a view of the full agent-to-agent conversation for each completed request
- The conversation shall include agent name, role, and message content per turn

### FR-08: Feedback Collection

- The system shall present a 1–5 star rating widget after each AI response
- Ratings shall be stored in the `user_feedback` table linked to the `user_request_logs` record

### FR-09: Audit Logging

- Every AI request-response cycle shall be logged to `user_request_logs` with:
  - User ID (Jira username), helper name, input type, Jira issue ID
  - Request content, agent response, duration, status
  - Full chat history (JSONB), token usage per agent (JSONB)

### FR-10: Document Ingestion

- The system shall provide a function (`DocIngestionFunction`) to ingest CSV files from Azure Blob Storage into Azure AI Search indexes
- The function shall generate vector embeddings for each document using `text-embedding-ada-002`
- The function shall create the target index if it does not exist

---

## 4. Non-Functional Requirements

### NFR-01: Response Time

- Agent pipeline should complete within 60–120 seconds for typical requests
- The frontend shall poll until completion (up to ~23 minutes timeout)
- If the backend exceeds 10 minutes (Durable Functions limit), the run is terminated

### NFR-02: Availability

- The system targets Azure's SLA for Function Apps (~99.95%)
- No redundancy or failover is currently configured (single region)

### NFR-03: Security

- Jira credentials are never persisted to disk or database — memory only
- Azure services use managed identity in production; API keys used for local dev
- No row-level security on the audit tables — all logs are accessible to any DB user

### NFR-04: Scalability

- Azure Durable Functions auto-scales for concurrent users
- Each user session is independent; no shared state between sessions
- Azure AI Search and Azure OpenAI are shared resources — high concurrent usage may hit rate limits

### NFR-05: Observability

- All requests logged to PostgreSQL with duration, status, chat history, and token counts
- No application-level alerting or monitoring dashboard currently configured
- Azure Function App logs available in Azure Monitor / Application Insights (if configured)

### NFR-06: Prompt Manageability

- Agent prompts stored in `agent_prompts` DB table with versioning
- Prompts can be updated without code re-deployment
- System falls back to hardcoded prompts if DB rows are missing (silent fallback — see constraints)

---

## 5. Constraints

1. **Azure-only** — managed identity, Durable Functions, and Azure AI Search are Azure-specific; not portable to AWS/GCP without significant rework
2. **Jira Xray plugin required** for TCG push (Xray REST API at `/rest/raven/1.0/`)
3. **Jira custom field IDs are hardcoded** — `customfield_12077`, `customfield_10125`, `customfield_10127` are specific to the configured Jira instance and must be remapped for any other instance
4. **AI Search indexes must be manually seeded** — no automated pipeline to keep them updated as new stories/tests are created in Jira
5. **No automated tests** — no unit tests, integration tests, or end-to-end tests found in the codebase
6. **No database migration tooling** — schema changes require manual SQL across all environments
7. **Single request per session** — no parallel AI calls from the same browser session (Streamlit limitation)
8. **Agent prompt DB call at import time** — `tcg_prompts.py` calls the DB at module load; missing DB row crashes the function cold start

---

## 6. Integration Points

### INT-01: Azure OpenAI
- Endpoint: `https://aio-az-openai-service1.openai.azure.com/`
- Models: `gpt-4o` (chat), `text-embedding-ada-002` (embeddings)
- API Version: `2024-02-01`
- Auth: API key (`AZURE_OPENAI_API_KEY`) or Managed Identity
- Used by: All agent chains (chat), DocIngestionFunction + AzureAISearchClient (embeddings)

### INT-02: Azure AI Search
- Endpoint: `https://sdlc-test-ai-search.search.windows.net`
- Auth: Admin key (`AZURE_SEARCH_ADMIN_KEY`)
- Indexes: `ras-helper-index-v1`, `tcg-manual-index-v1`, `tcg-cucumber-index-v1`
- Query type: Vectorized semantic search
- Used by: `AzureAISearchClient`, `DocIngestionFunction`

### INT-03: Azure PostgreSQL
- Server: `sdlc-test.postgres.database.azure.com`, database: `postgres`
- Auth: Username + password (local); Managed Identity (Azure-hosted)
- Tables: `agent_prompts`, `user_request_logs`, `user_feedback`
- Used by: `PromptManager` (backend), `PostgresClient` (frontend logging)

### INT-04: Azure Blob Storage
- Account: `sdlctest`
- Auth: Storage account key (`STORAGE_ACCOUNT_KEY`)
- Used by: `DocIngestionFunction` (CSV download), `file_uploader.py` (CSV upload)

### INT-05: Jira REST API v2
- Base URL: Configured via `JIRA_ENDPOINT` env var
- Auth: Basic Auth (base64 username:password)
- Custom fields: `customfield_12077` (ACs), `customfield_10125` (test type), `customfield_10127` (cucumber)
- Used by: `JiraClient` (both frontend and backend), `JiraTestCaseProcessor`

### INT-06: Jira Xray REST API
- Base URL: `{JIRA_ENDPOINT}/rest/raven/1.0/`
- Auth: Same Basic Auth as Jira
- Endpoints: Test step management
- Used by: `JiraClient.add_test_step_manual()`, `JiraClient.add_test_cucumber()`

---

## 7. Jira Field Mapping Reference

### Reading from Jira (story input)

| Field | Jira Path | Used for |
|-------|----------|---------|
| Issue key | `issue.key` | Identifier / audit |
| Summary | `fields.summary` | Displayed; passed to agents |
| Description | `fields.description` | Passed to agents |
| Acceptance Criteria | `fields.customfield_12077` | Passed to agents |
| Epic Link | `fields.customfield_10100` | Context enrichment (if present) |
| Issue type | `fields.issuetype.name` | Filter (Story type default) |
| Priority | `fields.priority.name` | Logged; used in TCG output |

### Writing to Jira (RAS push)

| Action | Endpoint | Fields written |
|--------|---------|---------------|
| Update story | `PUT /rest/api/2/issue/{id}` | `summary`, `description` |
| Add AC comment | `POST /rest/api/2/issue/{id}/comment` | Comment body with AC text |

### Writing to Jira (TCG push)

| Action | Endpoint | Fields written |
|--------|---------|---------------|
| Create Test | `POST /rest/api/2/issue/` | `summary`, `description`, `issuetype` (Test), `priority`, `customfield_10125` |
| Add manual step | `PUT /rest/raven/1.0/api/test/{key}/step` | `step`, `data`, `result` |
| Add cucumber | `PUT /rest/api/2/issue/{key}` | `customfield_10127` |
| Link Test→Story | `POST /rest/api/2/issueLink` | `type` (Tests), `inwardIssue`, `outwardIssue` |
