# SDLC-Agents — Project Documentation

> Complete project profile for teams onboarding without a knowledge transfer.
> Written from first-principles code review — April 2026.

---

## What Is This?

An AI-powered assistant for software delivery teams. It does two things:

1. **RAS — Requirement Analysis & Standardization**: Takes a raw requirement (free text or a Jira ticket) and rewrites it as an INVEST-compliant user story with title, description, and acceptance criteria.
2. **TCG — Test Case Generator**: Takes a user story and generates manual step-by-step test cases or Cucumber BDD scenarios, then pushes them directly into Jira as Test issues via Xray.

Everything is built around a multi-agent LLM pipeline (AutoGen) calling GPT-4o on Azure.

---

## Document Index

| # | Document | What it covers |
|---|----------|---------------|
| [01](./01_tech_stack.md) | Tech Stack | Every library, Azure service, and why it was chosen |
| [02](./02_architecture.md) | Architecture | System diagram, agent wiring, data flows end-to-end |
| [03](./03_modules.md) | Module Reference | Every file — what it does, inputs, outputs, line references |
| [04](./04_component_status.md) | Component Status | What works, what is broken, known bugs with file references |
| [05](./05_deployment.md) | Deployment Guide | Env vars, Azure resources, local dev, CI/CD, DB setup |
| [06](./06_srs.md) | Software Requirements | Functional & non-functional requirements, constraints, Jira field map |
| [07](./07_v2_roadmap.md) | V2 Roadmap | What to build next, debt to pay, architectural improvements |
| [08](./08_external_dependencies.md) | External Dependencies | Every external service, setup requirements, and verification steps |

---

## 5-Minute Orientation

```
User (browser)
    │
    ▼
Streamlit frontend  ──────── Jira  (fetch issues / push results)
    │
    ▼  HTTP POST + polling
Azure Durable Functions
    │
    ├── ExecuteRAS   ──── AutoGen 4-agent chain ──── GPT-4o
    ├── ExecuteTCG   ──── AutoGen 4-agent chain ──── GPT-4o
    └── PushtoJira   ──── Jira REST + Xray API
         │
         └── supporting services:
               Azure AI Search  (semantic RAG context)
               Azure PostgreSQL  (prompts + audit logs)
               Azure Blob Storage  (CSV ingestion source)
```

The frontend is **Streamlit** (Python), the backend is **Azure Durable Functions** (Python). The AI layer is **AutoGen** wiring four specialist agents per workflow. Everything communicates via HTTP — the frontend polls the Durable Functions status API until work is done.
