# 05 — Deployment Guide

Everything needed to run this project from scratch.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11 | Both frontend and backend |
| Azure Functions Core Tools | v4 | Local backend dev |
| Azure CLI | latest | `az login` for managed identity (not needed if using API keys) |
| Node.js | (any LTS) | Required internally by Azure Functions Core Tools |

---

## Azure Resources — What Must Exist

| Resource | Name | Notes |
|----------|------|-------|
| Azure Function App | `func-mortgage-dev` | Python 3.11, Durable Functions extension |
| Azure OpenAI | `aio-az-openai-service1` | Must have `gpt-4o` and `text-embedding-ada-002` deployments |
| Azure AI Search | `sdlc-test-ai-search` | Must have 3 indexes created AND seeded (see below) |
| Azure PostgreSQL Flexible Server | `sdlc-test` | Database: `postgres`; 3 tables must be created (see below) |
| Azure Storage Account | `sdlctest` | Blob container for CSV ingestion files |
| Azure Managed Identity | System-assigned on Function App | For production auth |

---

## Environment Variables

### Root `.env` (used by both backend and frontend locally)

```bash
# PostgreSQL
POSTGRES_HOST=sdlc-test.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=<username>
POSTGRES_PASSWORD=<password>

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://sdlc-test-ai-search.search.windows.net
AZURE_SEARCH_ADMIN_KEY=<admin_key>

# Azure Storage
STORAGE_ACCOUNT_NAME=sdlctest
STORAGE_ACCOUNT_KEY=<storage_key>

# Azure OpenAI
AZURE_CHAT_MODEL_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_MODEL_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_ENDPOINT=https://aio-az-openai-service1.openai.azure.com/
AZURE_OPENAI_TEMPERATURE=0.3
AZURE_EMBEDDING=text-embedding-ada-002
AZURE_OPENAI_API_KEY=<api_key>
```

### Frontend-specific (also needed)

```bash
# Jira
JIRA_ENDPOINT=https://jira-<your-company>.com.au/
PROJ_KEY=<default_project_key>     # e.g. AIHQE

# Azure Function App URL (local dev: http://localhost:7071)
AZURE_FUNCTION_APP=https://func-mortgage-dev.azurewebsites.net
```

### Backend — Azure Functions (`local.settings.json` — NOT committed)

For local Azure Functions development, create `backend/local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "POSTGRES_HOST": "sdlc-test.postgres.database.azure.com",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "postgres",
    "POSTGRES_USER": "<username>",
    "POSTGRES_PASSWORD": "<password>",
    "AZURE_SEARCH_ENDPOINT": "https://sdlc-test-ai-search.search.windows.net",
    "AZURE_SEARCH_ADMIN_KEY": "<key>",
    "STORAGE_ACCOUNT_NAME": "sdlctest",
    "STORAGE_ACCOUNT_KEY": "<key>",
    "AZURE_CHAT_MODEL_NAME": "gpt-4o",
    "AZURE_OPENAI_API_VERSION": "2024-02-01",
    "AZURE_MODEL_DEPLOYMENT_NAME": "gpt-4o",
    "AZURE_OPENAI_ENDPOINT": "https://aio-az-openai-service1.openai.azure.com/",
    "AZURE_OPENAI_TEMPERATURE": "0.3",
    "AZURE_EMBEDDING": "text-embedding-ada-002",
    "AZURE_OPENAI_API_KEY": "<key>"
  }
}
```

---

## Azure Managed Identity Role Assignments (Production)

The Function App's system-assigned managed identity must have these RBAC roles:

| Azure Service | Role Required |
|--------------|--------------|
| Azure OpenAI resource | `Cognitive Services OpenAI User` |
| Azure AI Search resource | `Search Index Data Reader` |
| Azure PostgreSQL | `PostgreSQL Flexible Server AD Admin` (or explicit user grant) |
| Azure Storage Account | `Storage Blob Data Contributor` |

Without these, all backend calls fail with 401/403 in Azure even though the code is correct.

For local dev, the API keys in `.env` bypass managed identity entirely.

---

## Database Setup (Manual — no migration scripts exist)

Connect to `sdlc-test` PostgreSQL, database `postgres`, and run:

```sql
-- Agent prompts (loaded by PromptManager; falls back to hardcoded if empty)
CREATE TABLE IF NOT EXISTS agent_prompts (
    id                SERIAL PRIMARY KEY,
    ai_helper_name    VARCHAR(255),
    agent_name        VARCHAR(255),
    prompt_content    TEXT,
    prompt_parameter  TEXT,
    version           INT DEFAULT 1,
    created_at        TIMESTAMP DEFAULT NOW(),
    UNIQUE (ai_helper_name, agent_name, version)
);

-- Request audit log
CREATE TABLE IF NOT EXISTS user_request_logs (
    request_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lid                  VARCHAR(255),
    ai_helper_name       VARCHAR(255),
    segment              VARCHAR(255),
    jira_issue_id        VARCHAR(255),
    request_content      TEXT,
    original_response    TEXT,
    response_time        INT,
    request_status       VARCHAR(50),
    error_message        TEXT,
    chat_history         JSONB,
    tokens_used          JSONB,
    user_edited_response TEXT,
    is_edited            BOOLEAN DEFAULT FALSE,
    created_at           TIMESTAMP DEFAULT NOW()
);

-- User feedback (star ratings)
CREATE TABLE IF NOT EXISTS user_feedback (
    feedback_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id       UUID REFERENCES user_request_logs(request_id),
    lid              VARCHAR(255),
    ai_helper_name   VARCHAR(255),
    jira_issue_id    VARCHAR(255),
    segment          VARCHAR(255),
    rating           INT CHECK (rating BETWEEN 1 AND 5),
    created_at       TIMESTAMP DEFAULT NOW()
);
```

> **Important:** If the `agent_prompts` table exists but has no rows, the system uses hardcoded fallback prompts from `ras_prompts.py` / `tcg_prompts.py`. This is silent — no warning is shown.
>
> **Critical:** The `tcg_prompts.py` module calls `PromptManager.get_prompt("TCG", "team_prompt")` at import time. If this row is missing and the fallback raises instead of catching, `ExecuteTCG` will crash at cold start. Verify this row exists or patch the code (see Bug 1 in `04_component_status.md`).

---

## Azure AI Search — Index Setup

Indexes must be created and populated before semantic search works. If empty, agents still run but produce lower-quality output (no RAG context injected) — the app gives no warning.

### Step 1 — Prepare CSV files

Each CSV must have columns matching the index schema:
- `id`, `description`, `acceptance_criteria`, `summary`, `priority`, `story_point`, `epic_link`

For RAS index: populate with historical user stories from your Jira project.  
For TCG manual index: populate with existing manual test cases.  
For TCG cucumber index: populate with existing cucumber scenarios.

### Step 2 — Upload CSV to Azure Blob

Upload each CSV to a container in the `sdlctest` storage account.

### Step 3 — Trigger DocIngestionFunction

Call the Azure Function with:
```json
{
  "blob_name": "<your_file.csv>",
  "container_name": "<container>",
  "index_name": "ras-helper-index-v1"
}
```

Repeat for `tcg-manual-index-v1` and `tcg-cucumber-index-v1`.

The function will:
1. Download the CSV
2. Generate 1536-dim embeddings for each row via `text-embedding-ada-002`
3. Create the index if it doesn't exist (HNSW vector config, cosine distance)
4. Upsert all documents

**Index names expected by the code:**
- `ras-helper-index-v1`
- `tcg-manual-index-v1`
- `tcg-cucumber-index-v1`

If you use different names, update `AzureAISearchClient` constants accordingly.

---

## Local Development Setup

### Backend (Azure Durable Functions)

```bash
# Prerequisites: Python 3.11, Azure Functions Core Tools v4

cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy root .env values into local.settings.json (see template above)
# DO NOT use az login unless testing managed identity

func start
```

Backend available at: `http://localhost:7071`  
Orchestrator endpoint: `http://localhost:7071/api/DurableFunctionsOrchestrator`

### Frontend (Streamlit)

```bash
cd frontend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy root .env and add:
# AZURE_FUNCTION_APP=http://localhost:7071
# JIRA_ENDPOINT=https://jira-<company>.com.au/
# PROJ_KEY=<your_project_key>

streamlit run src/app.py
```

Frontend available at: `http://localhost:8501`

---

## CI/CD Pipeline (Backend Only)

**File:** `.github/workflows/main_func-mortgage-dev.yml`

| Step | What happens |
|------|-------------|
| Trigger | Push to `main` branch |
| Python setup | 3.11 |
| Install | `pip install -r backend/requirements.txt` |
| Package | ZIP the `backend/` folder |
| Deploy | Azure Functions Action using `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` secret |

**Frontend has no pipeline.** The Streamlit app must be deployed manually (e.g., Azure App Service, Azure Container Apps, or a VM).

---

## Deployment Constraints

1. **No frontend CI/CD.** Streamlit must be deployed manually or a new pipeline built.

2. **API keys vs. Managed Identity.** The `.env` now has explicit API keys — these work locally and in Azure. Managed Identity is still needed if you want to remove secrets from the environment entirely. Both can coexist.

3. **AI Search indexes must be pre-seeded.** Empty indexes = no RAG context = generic (lower quality) output. The app will not error — quality drop is silent.

4. **No schema migration tooling.** If the DB schema changes in V2, you must manually `ALTER TABLE` in every environment. High drift risk.

5. **Prompts in DB are optional but risky.** System falls back to hardcoded prompts silently. `tcg_prompts.py` has a module-level DB call that can crash cold start if the `team_prompt` row is missing.

6. **Azure Function timeout.** Durable Functions activity timeout is 10 minutes. Complex AutoGen conversations (many review cycles) approaching this limit will be killed silently. The frontend poll will eventually give up after ~23 minutes.

7. **Jira credentials are user-provided at runtime.** No service account. Every user logs in with personal credentials. Session state is wiped on browser refresh.

8. **Jira custom field IDs are instance-specific.** `customfield_12077` (ACs), `customfield_10125` (test type), `customfield_10127` (cucumber) are hardcoded. These IDs will differ on a different Jira instance.

9. **Single region.** No geo-redundancy, no failover.

10. **Duplicate requests on double-click.** No idempotency key on orchestration start. Each click bills tokens and runs a full agent chain.
