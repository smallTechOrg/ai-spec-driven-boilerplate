# Sourcing Agent

> **All commands run from the repo root.**

An AI agent that helps real-estate / construction project teams source raw
materials (bricks, cement, steel, sand, etc.). Submit a sourcing request via a
web form — the agent researches suppliers, normalizes their offerings, scores
them against your criteria, and renders a ranked recommendation report.

The agent runs fully offline in **stub mode** (no API keys required) — the UI
shows a clear banner when stubs are active. Set the API keys to use real
providers; no other flag flip is needed.

---

## Stack

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- FastAPI + Jinja2 (server-rendered HTML)
- LangGraph (research → enrich → score → finalize)
- PostgreSQL (SQLAlchemy 2.0 + Alembic, psycopg2 driver)
- LLM: **Gemini** via `google-genai` (stub fallback when no key)
- Search: **Tavily** via `tavily-python` (stub fallback when no key)

---

## Prerequisites

- Python 3.12+, `uv` installed
- PostgreSQL 14+ running locally
- Two databases created (one for the app, one for tests):

```bash
createdb sourcing
createdb sourcing_test
```

---

## Setup

All commands below run from the **repo root**.

```bash
# 1. Install dependencies (app + dev)
uv sync --extra dev

# 2. Copy env template and edit if needed
cp .env.example .env

# 3. Apply database migrations
uv run alembic upgrade head

# 4. Verify migrations applied (must print a revision hash, not blank)
uv run alembic current
```

If `alembic current` prints nothing, the migration did not apply — fix
`SOURCING_DATABASE_URL` in `.env` and try again.

---

## Run the app

```bash
uv run python -m sourcing_agent
```

Open <http://127.0.0.1:8000>. The form page lets you submit a sourcing
request; you will be redirected to the ranked report at `/runs/<run_id>`.

Use **stub mode** (no keys) for an offline demo — every page shows a yellow
"Demo / stub mode" banner. To switch to real providers, set both:

```env
SOURCING_GEMINI_API_KEY=...
SOURCING_TAVILY_API_KEY=...
```

The banner disappears automatically once both keys are set.

---

## Run the tests

```bash
# Tests use SOURCING_TEST_DATABASE_URL (defaults to sourcing_test on localhost).
uv run pytest -v
```

Expected: **10 passed**.

The suite includes a golden-path UI smoke test that walks the full user
journey (form → submit → report → recent-runs list) and asserts response
content, not just status codes.

---

## Project layout

```
src/sourcing_agent/
├── api/         — FastAPI routes + Jinja templates wiring
├── config/      — Pydantic Settings (env-driven; provider=auto resolution)
├── db/          — SQLAlchemy 2.0 models, session factory
├── domain/      — Pydantic models used at module boundaries
├── graph/       — LangGraph state machine (state, nodes, edges, runner)
├── llm/         — Gemini provider + stub provider
├── search/      — Tavily provider + stub provider
├── prompts/     — .md prompt templates loaded at runtime
├── templates/   — base.html, form.html, report.html, runs.html
└── tools/       — research / enrich / score (pure functions over providers)

tests/
├── unit/        — config, db models
└── integration/ — end-to-end pipeline + golden-path UI smoke
```

---

## What's deferred (Future Phases)

- Multi-material concurrent sourcing per request
- Persistent supplier knowledge base + dedup across runs
- RFQ email drafting + response tracking
- Scheduled re-sourcing (price/availability watch)
- Auth + multi-org

See `spec/product/01-vision.md` for the full v0.1 scope and out-of-scope list.
