# Backend for SDLC Agent

This directory contains the backend services for the SDLC Agent application. The backend is responsible for handling AI-powered requirement rewriting, Jira integration, database operations, and Azure Function endpoints.


## Project Structure

```
backend/
  .env                      # Environment variables for backend services
  .gitignore                # Git ignore rules
  README.md                 # Project documentation
  requirements.txt          # Python dependencies
  agents/                   # Agent logic for RAS (Requirement Analysis & Standardization) and TCG (Test Case Generator)
    ras/
    tcg/
  common/                   # Shared modules and utilities
    __init__.py
    ai_search/
    db/
    jira/
    llm/
    prompts/
    utils/
  DocIngestionFunction/     # Azure Function for document ingestion
    __init__.py
    function.json
  DurableFunctionsHttpStart/    # Azure Durable Function HTTP starter
    __init__.py
    function.json
  DurableFunctionsOrchestrator/ # Azure Durable Function orchestrator
    __init__.py
    function.json
  ExecuteRAS/               # Azure Function for executing RAS agent
    __init__.py
    function.json
  ExecuteTCG/               # Azure Function for executing TCG agent
    __init__.py
    function.json
  PushtoJira/               # Azure Function for pushing data to Jira
    ...
```
## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd sdlc-agent/backend

2. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up environment variables:**
    Copy .env.example to .env and update the values as needed.
    ```bash
    cp .env.example .env
    ```