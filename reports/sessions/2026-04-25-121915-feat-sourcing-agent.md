# Session — Sourcing Agent (v0.1)

**Branch:** feat/sourcing-agent
**Started:** 2026-04-25 12:19:15
**Phase:** Stage 4 (scaffold) → Phase 1 → Phase 2

## Goal

Zero-shot build of a **Sourcing Agent** for real-estate / construction materials
(bricks, cement, steel, sand). Given a sourcing request (material, qty, location,
budget, timeline, criteria) the agent: researches suppliers (Tavily) → enriches /
normalizes (Gemini) → scores against user criteria → renders a ranked report.

## Intake answers

- **Scope:** narrow core loop — single material per request, web-form trigger.
- **Stack:** Python + PostgreSQL + local.
- **Trigger / output:** Web UI only (form submit → ranked report page).
- **Constraints / keys available:** Gemini API key, Tavily API key.

## Stack chosen

- Python 3.12, uv
- FastAPI + Jinja2 (server-rendered HTML)
- LangGraph (research → enrich → score → finalize)
- PostgreSQL via SQLAlchemy 2.0 + Alembic (psycopg2)
- LLM: Gemini (`google-genai`) with `provider=auto` → stub fallback
- Search: Tavily (`tavily-python`) with stub fallback
- Tests: pytest against PostgreSQL

## Stages

- [x] Intake (4-question round)
- [x] Approval gate (one-shot)
- [ ] Scaffold (in progress)
- [ ] Phase 1 — domain + schema + Alembic + repo CRUD tests
- [ ] Phase 2 — stubbed graph + web UI + golden-path smoke + README
- [ ] Drift check

## Steps log

- 12:19 — Branched `feat/sourcing-agent` off main; ran `reset.sh`.
- 12:19 — Session report opened.
