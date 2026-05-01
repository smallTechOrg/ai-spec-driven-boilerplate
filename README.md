# Lead Gen Agent

> **All commands run from the repo root** (`/Users/sai/Workspace/Code/ai-spec-driven-boilerplate`). Every shell block below assumes that working directory.

Discovers small-to-medium European businesses likely lacking an in-house data function, scores them as prospects, and surfaces the ranked list with CSV export.

Pipeline: `search → extract → score → persist` (LangGraph). Stub LLM by default; swap in Gemini by setting `GEMINI_API_KEY`.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 14+ running locally
- Two databases created (you can use any user/password — adjust `.env` accordingly):

```bash
# working dir: repo root
createdb lead_gen_agent
createdb lead_gen_agent_test
```

## Setup

```bash
# working dir: repo root
cp .env.example .env
# Edit .env so LEADGEN_DATABASE_URL points at your lead_gen_agent DB.

uv sync
uv run alembic upgrade head
uv run alembic current   # must print a revision hash, not blank
```

## Run the app

```bash
# working dir: repo root
uv run python -m lead_gen_agent
# serves on http://localhost:8001
```

Open http://localhost:8001, pick a country / industry / size band, and trigger a run. Results appear on `/leads`. CSV export at `/leads.csv`.

Without `GEMINI_API_KEY` set, the app runs in **stub mode** and every page shows a visible stub banner. Set `GEMINI_API_KEY` in `.env` and restart to use real Gemini.

## Test

Point `LEADGEN_DATABASE_URL` at the `_test` database, then:

```bash
# working dir: repo root
LEADGEN_DATABASE_URL=postgresql+psycopg2://sai@localhost:5432/lead_gen_agent_test uv run pytest
```

Tests hit real PostgreSQL (never SQLite, per repo rule 5). No `GEMINI_API_KEY` required — stub mode.

## Health check

```bash
# working dir: repo root
curl http://localhost:8001/health
# {"status":"ok"}
```

## Project layout

- `src/lead_gen_agent/` — the agent package
  - `config/` — pydantic-settings (prefix `LEADGEN_`, `extra="ignore"`)
  - `db/` — SQLAlchemy models + session + repository
  - `domain/` — Pydantic models (`Filters`, `Candidate`, `Lead`, `Run`)
  - `graph/` — LangGraph state, nodes, agent, runner
  - `llm/` — `LLMClient` + Gemini + Stub providers
  - `tools/search.py` — `SearchTool` protocol + DuckDuckGo + Stub
  - `api/` — FastAPI routes, Jinja templates, static assets
- `tests/unit/` — unit tests (CRUD, config)
- `tests/integration/` — pipeline end-to-end + golden-path UI smoke
- `alembic/` — migrations
- `spec/` — product + engineering spec (read `CLAUDE.md` first)
- `reports/sessions/` — per-session reports (see `reports/implementation-plan.md` for roadmap)

## Phase status

- **Phase 1** — domain models + Postgres schema: DONE
- **Phase 2** — stubbed agent loop + FastAPI/Jinja UI + CSV export: DONE
- **Phase 3+** — real Gemini + DuckDuckGo integration, resilience, enrichment, outreach: NOT STARTED

See `reports/implementation-plan.md`.
