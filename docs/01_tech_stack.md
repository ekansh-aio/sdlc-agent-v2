# 01 — Tech Stack

---

## Backend

| Layer | Technology | Version / ID | Why it was chosen |
|-------|-----------|-------------|-------------------|
| Language | Python | 3.11 | Team familiarity; AutoGen is Python-native |
| Serverless compute | Azure Durable Functions | v2, extension bundle 4.x | Agent chains take 30–120 s — standard Functions time out at 230 s; Durable adds polling API so frontend can track live progress |
| Agent orchestration | AutoGen (`autogen-agentchat`, `autogen-core`, `autogen-ext`) | latest | Managed multi-agent loop with `SelectorGroupChat`; avoids manually wiring sequential LLM calls |
| LLM | Azure OpenAI — `gpt-4o` | API version `2024-02-01`, deployment `gpt-4o` | Best available reasoning model at time of build |
| Embeddings | Azure OpenAI — `text-embedding-ada-002` | 1536-dim vectors | Used for RAG semantic search |
| Vector / semantic search | Azure AI Search | REST via `azure-search-documents` | Finds similar historical requirements/test cases to ground GPT output (RAG pattern) |
| Database | Azure PostgreSQL Flexible Server | `sdlc-test`, db `postgres` | Stores agent prompts (so they can change without redeploy), request logs, and user feedback ratings |
| Auth | Azure Managed Identity / `DefaultAzureCredential` | `azure-identity` | Passwordless auth when running in Azure; API keys used for local dev |
| Blob storage | Azure Storage Blob | account `sdlctest` | Holds CSV files fed into `DocIngestionFunction` for index seeding |
| Jira test management | Xray REST API | Jira Server plugin | Creates Test issues and manual/cucumber steps natively |

### Backend `requirements.txt` (notable packages)

```
autogen-agentchat
autogen-ext[azure]
autogen-ext[openai]
autogen-core
azure-functions
azure-durable-functions
azure-identity
azure-storage-blob
azure-search-documents
azure-keyvault-secrets
openai
psycopg2-binary
python-dotenv
requests-oauthlib
```

---

## Frontend

| Layer | Technology | Why |
|-------|-----------|-----|
| UI framework | Streamlit | Python-native, QE engineers can modify without frontend skills |
| Jira client | `requests` + custom wrapper | Thin wrapper around Jira REST API v2 |
| DB client | `psycopg2-binary` | Direct PostgreSQL driver for logging |
| Excel reader | `openpyxl` + `pandas` | File-upload input path (not yet wired to UI) |
| Clipboard | `pyperclip` | Copy-to-clipboard button |
| Rating | Custom star/emoji widgets | In-app feedback collection |

### Frontend `requirements.txt` (notable packages)

```
streamlit
streamlit-extras
pandas
requests
pyperclip
openpyxl
psycopg2-binary
python-dotenv
azure-storage-blob
azure-identity
autogen-agentchat
autogen-ext[azure]
autogen-ext[openai]
```

> The frontend `requirements.txt` includes AutoGen packages. These are not used by the frontend itself — they appear to be copy-paste leftovers from the backend and add unnecessary install weight.

---

## DevOps / Infrastructure

| Tool | Purpose |
|------|---------|
| GitHub Actions | CI/CD — deploys backend to Azure Functions on push to `main` |
| Azure Functions Core Tools v4 | Local dev and manual deploy |
| Azure CLI | `az login` for local managed-identity testing |

---

## Azure Resources in Use

| Resource | Name | Purpose |
|----------|------|---------|
| Azure Function App | `func-mortgage-dev` | Hosts backend |
| Azure OpenAI | `aio-az-openai-service1` | `gpt-4o` and `text-embedding-ada-002` |
| Azure AI Search | `sdlc-test-ai-search` | 3 semantic indexes |
| Azure PostgreSQL | `sdlc-test` | Prompts + audit |
| Azure Storage Account | `sdlctest` | CSV blobs for ingestion |
| Azure Managed Identity | Assigned to `func-mortgage-dev` | Passwordless auth in production |

---

## Key Architectural Decisions (and trade-offs)

### Why Durable Functions?
AutoGen `run_stream()` can run for 1–2 minutes. Standard Azure Functions time out at 230 s. Durable Functions support arbitrarily long activity execution and expose a polling status URI (`statusQueryGetUri`) so the Streamlit frontend can display a spinner while waiting.

**Trade-off:** Adds orchestration overhead. If the agent loop goes into a retry spiral (e.g., ReviewerAgent keeps failing), the function runs until the 10-minute Durable timeout and kills silently.

### Why AutoGen `SelectorGroupChat`?
`SelectorGroupChat` lets you define agents declaratively and wire a selector LLM to decide who speaks next. This replaces a brittle `if agent == X: call Y` chain. The selector prompt is stored in PostgreSQL so routing logic can be tuned without re-deploying.

**Trade-off:** If the PostgreSQL `agent_prompts` table is empty, the system falls back to hardcoded prompts in Python files — but does so silently.

### Why Streamlit?
QE engineers (not front-end developers) need to maintain this. Streamlit lets them write Python and get a working web UI. No React, no Node, no build pipeline.

**Trade-off:** Streamlit re-runs the entire script on every interaction. Session state must be managed carefully. Browser refresh wipes all session data — users must re-authenticate every session.

### Why RAG (Azure AI Search)?
Without examples, GPT-4o generates generic test cases. By retrieving 3 historical test cases (or user stories) from the project's own history and injecting them into context, the agents produce output that matches the team's naming conventions, vocabulary, and structure.

**Trade-off:** The indexes must be manually seeded via `DocIngestionFunction`. If they're empty, the system still works but output quality drops — with no warning to the user.
