# 02 — Architecture

---

## System Context Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                        USER  (Browser)                            │
└────────────────────────────┬──────────────────────────────────────┘
                             │  HTTPS
                             ▼
┌───────────────────────────────────────────────────────────────────┐
│                 FRONTEND  (Streamlit — Python)                    │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  Jira Auth UI   │  │  RAS / TCG Forms │  │  PG Audit Log   │  │
│  │  (dialogs.py)   │  │  (app.py)        │  │  (pgdb_ops.py)  │  │
│  └────────┬────────┘  └────────┬─────────┘  └─────────────────┘  │
│           │                   │                                   │
└───────────┼───────────────────┼───────────────────────────────────┘
            │ Jira REST          │  HTTP POST  (trigger)
            │ Basic Auth         │  HTTP GET   (poll statusQueryGetUri)
            ▼                   ▼
┌──────────────────┐   ┌────────────────────────────────────────────┐
│  Jira Instance   │   │       AZURE DURABLE FUNCTIONS              │
│  (company Jira)  │   │                                            │
│                  │   │  ┌─────────────────────────────────────┐   │
│  • Fetch issues  │   │  │  DurableFunctionsHttpStart          │   │
│  • Update fields │   │  │  (HTTP trigger — entry point)       │   │
│  • Create Tests  │   │  └──────────────┬──────────────────────┘   │
│  • Link issues   │   │                 │ starts orchestration      │
│  • Add steps     │   │  ┌──────────────▼──────────────────────┐   │
│                  │   │  │  DurableFunctionsOrchestrator       │   │
└──────────────────┘   │  │  (routes by helper_name + activity) │   │
       ▲               │  └──────┬──────────────┬───────────────┘   │
       │               │         │              │                   │
       │               │  ┌──────▼──────┐ ┌────▼──────┐ ┌────────┐ │
       │               │  │ ExecuteRAS  │ │ExecuteTCG │ │PushTo  │ │
       │               │  │ (activity)  │ │(activity) │ │Jira    │─┼──┐
       │               │  └──────┬──────┘ └────┬──────┘ └────────┘ │  │
       │               └─────────┼─────────────┼────────────────────┘  │
       │                         │             │                        │
       │                         ▼             ▼                        │
       │               ┌─────────────────────────────────────────────┐ │
       │               │         AZURE SERVICES                      │ │
       │               │                                             │ │
       │               │  ┌────────────────┐  ┌──────────────────┐  │ │
       │               │  │  Azure OpenAI  │  │  Azure AI Search │  │ │
       │               │  │  gpt-4o        │  │  3 indexes       │  │ │
       │               │  │  ada-002 embed │  │  (RAG context)   │  │ │
       │               │  └────────────────┘  └──────────────────┘  │ │
       │               │                                             │ │
       │               │  ┌─────────────────────────────────────┐   │ │
       │               │  │  Azure PostgreSQL  (sdlc-test)      │   │ │
       │               │  │  • agent_prompts                    │   │ │
       │               │  │  • user_request_logs                │   │ │
       │               │  │  • user_feedback                    │   │ │
       │               │  └─────────────────────────────────────┘   │ │
       │               │                                             │ │
       │               │  ┌─────────────────────────────────────┐   │ │
       │               │  │  Azure Blob Storage  (sdlctest)     │   │ │
       │               │  │  • CSV files for DocIngestion       │   │ │
       │               │  └─────────────────────────────────────┘   │ │
       │               └─────────────────────────────────────────────┘ │
       └───────────────────────────────────────────────────────────────┘
                    PushtoJira calls Jira REST + Xray API
```

---

## Agent Architecture — RAS

```
ExecuteRAS  (Azure Durable Activity Function)
│
└── AutoGen  SelectorGroupChat
    │
    │  selector_prompt (from agent_prompts DB or ras_prompts.py fallback)
    │  decides who speaks next based on conversation history
    │
    ├── [1] RequestHandlerAgent
    │       Role: Gateway — decides whether to call semantic search
    │       input_type == "jira_id":
    │         → calls semantic_search_ras() tool
    │         → returns JSON: { user_query, retrieved_context: [{description, summary, ac}] }
    │       input_type == "text_input":
    │         → passes raw text directly to AnalyserAgent
    │       Speaks exactly ONCE per run
    │
    ├── [2] AnalyserAgent
    │       Role: Expert Business Analyst
    │       Input: RequestHandlerAgent JSON (with or without retrieved_context)
    │       Task: Write INVEST-compliant user story
    │             Title / Description (Who/What/Why) / AC (Given-When-Then) / Priority
    │       If ReviewerAgent returns FAILED → revise and resend
    │       If ReviewerAgent returns SUCCESS → stop
    │
    ├── [3] ReviewerAgent
    │       Role: Senior Business Analyst
    │       Validates story against INVEST principles
    │       FAILED  → detailed feedback back to AnalyserAgent
    │       SUCCESS → passes { "finalResult": "SUCCESS" } to FinalResponseGeneratorAgent
    │       Never writes a story itself
    │
    └── [4] FinalResponseGeneratorAgent
            Role: Formatter only
            Triggered by: message from ReviewerAgent containing "finalResult": "SUCCESS"
            Output format:
              **Title:** <title>
              **Description:** <description>
              **Acceptance Criteria:**
              **AC01:** <criteria>
              **AC02:** <criteria>
              **Priority:** <High|Medium|Low>
              TERMINATE
            Termination: keyword "TERMINATE" ends the run

Termination conditions (ExecuteRAS/__init__.py):
  • Text "TERMINATE" detected in any message
  • Any message mentions "TERMINATE"
  • Max 26 messages reached (safety circuit-breaker)
```

---

## Agent Architecture — TCG

```
ExecuteTCG  (Azure Durable Activity Function)
│
└── AutoGen  SelectorGroupChat
    │
    ├── [1] RequestHandlerAgent  (called DataExtractorAgent in TCG prompts)
    │       input_type == "text_input":
    │         → passes text directly to AnalyserAgent, speaks once
    │       input_type == "jira_id" + issue_type "Manual":
    │         → calls semantic_search_tcg_manual() tool
    │         → returns matched manual test examples + user input
    │       input_type == "jira_id" + issue_type "Automatic":
    │         → calls semantic_search_tcg_cucumber() tool
    │         → returns matched cucumber examples + user input
    │
    ├── [2] AnalyserAgent  (prompt varies by test_type)
    │       Manual mode:
    │         Generates test cases with:
    │           TestCaseID   — "<parent_id> - TC 01"
    │           Summary      — includes parent ID
    │           Description  — plain language scenario
    │           ManualSteps  — array of {Action, Data, ExpectedResult}
    │           Priority     — High/Medium/Low (risk-based)
    │         Ships 3 worked examples (AIHQE-300, AIHQE-311, AIHQE-313)
    │
    │       Cucumber/Automatic mode:
    │         Same fields but replaces ManualSteps with:
    │           cucumber_steps — "Given … When … Then …" string (no step defs)
    │         Ships 3 worked cucumber examples
    │
    │       Feedback loop: FAILED → revise, SUCCESS → stop
    │
    ├── [3] ReviewerAgent
    │       Reviews: coverage, correctness, clarity, completeness
    │       FAILED → detailed feedback to AnalyserAgent
    │       SUCCESS → passes approved test cases as "finalData" list
    │
    └── [4] FinalResponseGeneratorAgent
            Output (Manual):
              {
                "finalData": [
                  {
                    "TestCaseID":   "AIHQE-300 - TC 01",
                    "Summary":      "...",
                    "Description":  "...",
                    "ManualSteps":  [{"Action":"...", "Data":"...", "ExpectedResult":"..."}],
                    "Priority":     "High"
                  }, ...
                ],
                "status": "TERMINATE"
              }

            Output (Cucumber):
              {
                "finalData": [
                  {
                    "TestCaseID":      "AIHQE-300 - TC 01",
                    "Summary":         "...",
                    "Description":     "...",
                    "cucumber_steps":  "Given ...\nWhen ...\nThen ...",
                    "Priority":        "High"
                  }, ...
                ],
                "status": "TERMINATE"
              }

Termination conditions (ExecuteTCG/__init__.py):
  • "status": "TERMINATE" in JSON response
  • Max 16 messages reached
```

---

## Full Data Flow — RAS (End-to-End)

```
1.  User opens browser → Streamlit app loads
2.  Jira auth dialog → user enters Jira username + password
      → jira_client.authenticate_user()  →  GET /rest/api/2/myself
      → stored in st.session_state.jira_username / jira_password

3.  Sidebar: select "Requirement Analysis & Standardization"
4.  Select input type: "Jira ID" or "Free Text Requirement"

─── PATH A: Jira ID ───────────────────────────────────────────────
5a. Multiselect shows issues from  GET /rest/api/2/search?jql=...
6a. User picks an issue ID (e.g. PROJ-123)
7a. Frontend fetches  GET /rest/api/2/issue/PROJ-123
      → extracts: summary, description, customfield_12077 (ACs)
8a. Displays issue details in expander
9a. User clicks "Analyse"
10a. Payload:  { helper_name:"RAS", requirement:"<concatenated fields>",
                 input_type:"jira_id", activity:"get_data" }

─── PATH B: Free Text ─────────────────────────────────────────────
5b. User types requirement text
6b. Validation: ≥3 words, no garbage/special-char-only input
7b. User clicks "Analyse"
8b. Payload:  { helper_name:"RAS", requirement:"<text>",
                input_type:"text_input", activity:"get_data" }

─── COMMON ────────────────────────────────────────────────────────
11. POST  {AZURE_FUNCTION_APP}/api/DurableFunctionsOrchestrator
12. Durable Functions returns:  { statusQueryGetUri, id }
13. Frontend polls  statusQueryGetUri  every 20 s, up to 70 tries (≈23 min)
      → waits for  runtimeStatus == "Completed"

14. ExecuteRAS activity runs:
      a. LLMConfig reads AZURE_OPENAI_API_KEY → builds AzureOpenAIChatCompletionClient
      b. PromptManager loads prompts from agent_prompts table (or fallback hardcoded)
      c. Builds 4-agent SelectorGroupChat
      d. Runs team.run_stream(requirement)
      e. Collects messages; extracts FinalResponseGeneratorAgent's last message
      f. Strips "TERMINATE" suffix
      g. Returns: { response, chat_history, agent_token_usage }

15. Frontend receives result:
      → Displays formatted markdown story in expander
      → Shows "Analyse Agents" button → chat dialog with full agent history
      → Star rating saved to user_feedback table
      → "Copy" button → pyperclip

16. User optionally edits in text area
17. User clicks "Approve & Push to Jira"
      Payload:  { helper_name:"RAS", title, description, acceptance_criteria,
                  base_url, jira_id, jira_username, jira_password, activity:"PushtoJira" }

18. PushtoJira activity:
      → JiraClient.update_jira_issue(jira_id, title, description, ac)
      → PUT /rest/api/2/issue/{jira_id}  with fields payload
      → POST /rest/api/2/issue/{jira_id}/comment  with AC text (if present)

19. Frontend logs to PostgreSQL:
      user_request_logs  (input, response, duration, chat_history, tokens)
      user_feedback      (rating, request_id)
```

---

## Full Data Flow — TCG (End-to-End)

```
1–4.  Same auth + sidebar steps as RAS
5.    User selects "Test Case Generator"
6.    Radio: "Manual" or "Automated"
7.    Select input type: Jira ID or Free Text

8.  ExecuteTCG receives payload:
      { helper_name:"TCG", input_type, issue_type:"Manual"|"Automatic",
        request_data:"<story text>", process_type:"get_data" }

9.  Agent chain runs (same pattern as RAS, different prompts + JSON output)

10. Frontend receives finalData JSON array
      → Renders each test case as a card with fields expanded
      → Edit mode available per test case

11. "Approve & Push to Jira":
      Payload:  { helper_name:"TCG", issue_type, request_data:"<test_cases_json>",
                  proj_key, jira_id, base_url, jira_username, jira_password,
                  process_type:"push_data", activity:"PushtoJira" }

12. PushtoJira activity:
      → JiraTestCaseProcessor.processing_data_to_jira_manual() or _cucumber()
      For each test case:
        a. POST /rest/api/2/issue/  →  creates Test issue (type "Test")
             fields: summary, description, priority, customfield_10125 (test type)
        b. For Manual:
             PUT /rest/raven/1.0/api/test/{key}/step  →  adds each step
        c. For Cucumber:
             PUT /rest/api/2/issue/{key}  →  sets customfield_10127 (cucumber text)
        d. POST /rest/api/2/issueLink  →  links Test → parent Story ("Tests" link)

13. Frontend logs to PostgreSQL
```

---

## Document Ingestion Flow (Index Seeding)

```
DocIngestionFunction (one-time / manual trigger)
│
├── Input:  { blob_name, container_name, index_name }
│
├── Download CSV from Azure Blob (sdlctest account)
│
├── For each row in CSV:
│     a. Clean text (strip markdown, control chars, collapse whitespace)
│     b. Concatenate description + acceptance_criteria
│     c. POST to Azure OpenAI embeddings  →  1536-dim vector
│     d. Build document: { id, description, acceptance_criteria, summary,
│                           priority, story_point, epic_link, metadata, embedding }
│
├── If index doesn't exist: create it with HNSW vector config
│
└── Upsert all documents into Azure AI Search index

Indexes created this way:
  ras-helper-index-v1        (historical user stories)
  tcg-manual-index-v1        (historical manual test cases)
  tcg-cucumber-index-v1      (historical cucumber scenarios)
```

---

## Database Schema

```
PostgreSQL — sdlc-test  (database: postgres)

agent_prompts
├── id                  SERIAL PK
├── ai_helper_name      VARCHAR(255)   — 'RAS' | 'TCG'
├── agent_name          VARCHAR(255)   — 'RequestHandlerAgent' | 'AnalyserAgent' |
│                                        'ReviewerAgent' | 'FinalResponseGeneratorAgent' |
│                                        'team_prompt' | 'selector_prompt'
├── prompt_content      TEXT           — full system prompt
├── prompt_parameter    TEXT           — optional extra params (rarely used)
├── version             INT            — auto-incremented; highest version wins
└── created_at          TIMESTAMP

user_request_logs
├── request_id          UUID PK
├── lid                 VARCHAR(255)   — Jira username (acting as user ID)
├── ai_helper_name      VARCHAR(255)   — 'RAS' | 'TCG'
├── segment             VARCHAR(255)   — 'text_input' | 'jira_id'
├── jira_issue_id       VARCHAR(255)   — Jira key (null for free-text runs)
├── request_content     TEXT           — what the user submitted
├── original_response   TEXT           — agent's formatted response
├── response_time       INT            — seconds to complete
├── request_status      VARCHAR(50)    — 'success' | 'failed'
├── error_message       TEXT
├── chat_history        JSONB          — full agent conversation array
├── tokens_used         JSONB          — {AgentName: {prompt_tokens, completion_tokens}}
├── user_edited_response TEXT          — post-edit content if user changed it
├── is_edited           BOOLEAN        — flag: was response edited before push?
└── created_at          TIMESTAMP

user_feedback
├── feedback_id         UUID PK
├── request_id          UUID  →  user_request_logs.request_id
├── lid                 VARCHAR(255)
├── ai_helper_name      VARCHAR(255)
├── jira_issue_id       VARCHAR(255)
├── segment             VARCHAR(255)
└── rating              INT  (1–5 stars)
└── created_at          TIMESTAMP
```

---

## Jira Custom Fields (in Use)

| Field ID | Name | Used for |
|----------|------|---------|
| `customfield_12077` | Acceptance Criteria | Read from Story issues |
| `customfield_10100` | Epic Link | Read from issues (passed to search context) |
| `customfield_10125` | Test Type | Set when creating Test issues (Manual / Cucumber) |
| `customfield_10127` | Cucumber Steps | Set when pushing cucumber test cases |

These field IDs are **Jira-instance specific**. If deploying to a different Jira, these must be verified in the target instance.

---

## Azure AI Search — Index Schema

Each index uses the same schema:

```
id                  Edm.String         key=True
description         Edm.String         searchable
acceptance_criteria Edm.String         searchable
summary             Edm.String         searchable
priority            Edm.String         searchable
story_point         Edm.String         searchable
epic_link           Edm.String         searchable
metadata            Edm.String         filterable
embedding           Collection(Edm.Single)  dimensions=1536, HNSW, cosine
```

Semantic search config: top 3 results, score threshold ≥ 0.85.
