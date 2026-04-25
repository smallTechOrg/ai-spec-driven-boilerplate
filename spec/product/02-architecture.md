# Architecture

## System Overview

The Sourcing Agent is a single Python service composed of:
1. **FastAPI web layer** — serves the web UI (Jinja2 templates) and a JSON API
2. **LangGraph agent** — a directed graph that runs the sourcing pipeline (intake → research → rank → report)
3. **PostgreSQL database** — persists projects, material line items, sourcing runs, supplier candidates, and recommendations
4. **LLM provider layer** — wraps Google Gemini; falls back to a stub when no API key is set

## Components

| Component | Technology | Role |
|-----------|-----------|------|
| Web server | FastAPI + Uvicorn | Serve UI + JSON API |
| UI templates | Jinja2 | Project form, run status, report view |
| Agent graph | LangGraph | Orchestrate sourcing pipeline nodes |
| LLM provider | Google Gemini / Stub | Research and rank suppliers |
| Database | PostgreSQL + SQLAlchemy + Alembic | Persist all state |
| Config | Pydantic Settings | Environment variable management |

## Data Flow

```
User → Web Form → FastAPI → SourcingAgent.run()
                                 ↓
                         [LangGraph Graph]
                         intake_node → research_node(per material) → rank_node → report_node
                                 ↓
                         PostgreSQL (run + recommendations saved)
                                 ↓
                         FastAPI → Jinja2 → Report Page → User
```

## Key Design Decisions

- All agent state flows through a typed `AgentState` TypedDict (LangGraph standard)
- LLM provider is selected at startup: `GEMINI_API_KEY` set → real provider; unset → stub
- Each sourcing run is atomic: one `SourcingRun` row, with child `SupplierRecommendation` rows
- The web UI polls `/api/runs/{run_id}/status` until run completes, then redirects to report
