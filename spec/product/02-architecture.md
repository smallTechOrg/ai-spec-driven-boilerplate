# Architecture

## System Overview

The EU Lead Gen Agent is a locally-run web application. A data consultant fills a search form in the browser; the FastAPI server queues a LangGraph pipeline run that calls Gemini (with Google Search Grounding) to discover and enrich SMB leads; results are persisted in PostgreSQL and displayed in a browsable dashboard with CSV export.

## Component Map

```
Browser
    │  POST /runs  (criteria)
    ▼
FastAPI  ←────────────────────────  Jinja2 templates
    │
    ▼
LangGraph pipeline
    │
    ├── search_node  ──►  Gemini API (Google Search Grounding)
    │
    └── enrich_node  ──►  Gemini API (structured extraction)
    │
    ▼
PostgreSQL  (leads, search_runs)
    │
    ▼
FastAPI  GET /leads  ──►  Dashboard + CSV export
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| Web (FastAPI + Jinja2) | Receive search criteria, serve dashboard, stream run status |
| Graph (LangGraph) | Orchestrate search → enrich pipeline per run |
| LLM (Gemini 2.5 Flash) | Discover company names; extract firmographic fields |
| Repository (SQLAlchemy) | Persist and query leads + search runs |
| Database (PostgreSQL) | Durable storage with dedup on company domain |

## Data Flow

1. **Trigger:** User submits the search form (country, industry, headcount range)
2. FastAPI creates a `SearchRun` record (status = `running`) and starts the LangGraph graph synchronously
3. `search_node` calls Gemini with a grounded prompt; extracts a list of company names + domains
4. `enrich_node` calls Gemini once per company; extracts firmographic fields and a "why fit" summary
5. `save_node` upserts each `Lead` into PostgreSQL (dedup on domain); marks run `completed`
6. **Output:** Leads visible in dashboard; downloadable as CSV

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|-------------|
| Google Gemini API | Lead discovery + enrichment | Set run status `failed`; surface error in UI |
| PostgreSQL | Persistent lead + run storage | App fails to start; logged loudly |

## Deployment Model

Local web server. Run with `uv run python -m lead_gen_agent` from the repo root. Listens on port 8001. No cloud deployment in v0.1.
