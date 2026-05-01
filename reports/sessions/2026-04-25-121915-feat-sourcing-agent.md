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
- [x] Scaffold
- [x] Phase 1 — domain + schema + Alembic + repo CRUD tests (5/5 PASS on PostgreSQL)
- [x] Phase 2 — stubbed graph + web UI + golden-path smoke + README (10/10 PASS, live `/health` 200, live `/` 200 with stub banner)
- [ ] Drift check

## Steps log

- 12:19 — Branched `feat/sourcing-agent` off main; ran `reset.sh`.
- 12:19 — Session report opened, .env.example + spec/product/* filled in.
- 12:25 — Phase 1 source written: config/settings.py, domain/models.py, db/models.py, db/session.py, alembic env+template+initial migration.
- 12:30 — `uv run alembic upgrade head` applied; `alembic current` = 4c54f7d953bf.
- 12:31 — `uv run pytest tests/unit -v` → 5/5 PASS. Phase 1 gate passed.
- 12:32 — Phase 1 committed; pushed to origin/feat/sourcing-agent.
- 12:33 — Phase 2 source written: llm/{stub,gemini,factory}, search/{stub,tavily,factory}, tools/{research,enrich,score}, graph/{state,nodes,edges,agent,runner}, api/{routes,__init__}, templates/{base,form,report,runs}, __main__.py, prompts/{enrich,score}.md.
- 12:35 — Tests written: tests/integration/{test_pipeline,test_web_smoke}.
- 12:36 — Initial `uv run pytest` → 9/10 (Jinja `run.items` collided with dict.items). Renamed to `recommendations`. 10/10 PASS.
- 12:37 — Live-server check: `uv run python -m sourcing_agent` started; `curl /health` → HTTP 200 `{"status":"ok"}`; `curl /` → HTTP 200 with form + stub banner. PASS.
- 12:38 — README rewritten to reflect Sourcing Agent setup; verified `uv run alembic current` and `uv run pytest` from a fresh shell.

## Future improvements (deferred)

- Real Tavily quality tuning + Gemini prompt iteration (Phase 3).
- Pagination on `/runs`.
- Background job for graph runs (currently synchronous on POST).
- Multi-material requests, supplier dedup across runs.
