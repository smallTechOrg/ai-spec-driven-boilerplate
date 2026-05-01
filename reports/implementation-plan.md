# Implementation Plan — Lead Gen Agent

## Phase 1 — Domain + Schema (DONE in this session)

- Pydantic domain models: `Filters`, `Candidate`, `Lead`, `Run`
- SQLAlchemy declarative: `RunRow`, `LeadRow` with FK cascade + indexes
- Repository layer: `create_run`, `complete_run`, `add_lead`, `list_runs`, `list_leads`
- Alembic config + initial migration
- pytest + Postgres-only conftest (truncate-between-tests)
- **Gate:** `uv run alembic upgrade head` + CRUD tests pass.

## Phase 2 — Stubbed Agent Loop + UI (this session)

- `tools/search.py` — DuckDuckGo HTML `SearchTool` protocol + stub
- `llm/providers/` — `Gemini`, `Stub` (branches on `<node:*>` tags only)
- `graph/{state,nodes,edges,agent,runner}.py` — `search → extract → score → persist`
- `api/` — FastAPI app + Jinja templates (base, index, runs, leads) + stub banner + CSV stream
- `__main__.py` — uvicorn on port 8001
- Integration test: full-pipeline via stub LLM
- Golden-path UI smoke test asserting content (banner, lead name, CSV header)
- Live-server curl check of `/health` + `/leads`
- README
- **Gate:** `uv run pytest` green with no `GEMINI_API_KEY`; live-server curl both 200.

## Phase 3 — Real integrations (future)

- Wire real DuckDuckGo HTML scraper
- Wire real Gemini extract + score
- End-to-end: ≥10 leads from one run

## Phase 4 — Resilience (future)

- Timeouts, retries on search + LLM
- Graceful degradation (0-lead run = still `completed`, not `failed`)
- Structured logging events

## Phase 5 — Enrichment (future)

- Org structure, LOBs, financial signals
- Paid data provider adapters (Apollo, Clearbit)

## Phase 6 — Outreach (future)

- Per-lead outreach copy generation
- Template library
