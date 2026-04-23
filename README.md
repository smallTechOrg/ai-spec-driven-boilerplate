# BlogForge

> **All commands run from the repo root** — the repo root *is* the project. Never `cd` into a subdirectory.

BlogForge is a local-first blog generator. Define a **Voice** (your tone/style guidelines), create **Writer** personas that embody it, then pick a writer + topic to produce an article via a LangGraph pipeline that calls Google Gemini. Articles are stored in PostgreSQL and viewable in a minimal web UI.

Stack: Python 3.12 · FastAPI + Jinja2 · PostgreSQL + SQLAlchemy + Alembic · LangGraph · Gemini.

---

## Prerequisites

- `uv`
- PostgreSQL running locally
- (Optional) A Google Gemini API key — the app runs against a deterministic stub provider if you don't have one.

## Setup (from repo root)

```bash
cp .env.example .env

createdb blogforge
createdb blogforge_test

uv sync
uv run alembic upgrade head
uv run alembic current   # must print a revision hash, not blank
```

## Run the app (stub / offline mode — default)

```bash
uv run python -m blogforge
```

Open http://localhost:8001, then:
1. Create a Voice (name + guidelines)
2. Create a Writer linked to that voice
3. Generate an article — pick the writer, enter a topic

## Run with real Gemini

In `.env`:

```
BLOGFORGE_LLM_PROVIDER=gemini
BLOGFORGE_GEMINI_API_KEY=your-key-here
BLOGFORGE_LLM_MODEL=gemini-2.5-flash
```

Then `uv run python -m blogforge`.

## Run tests

Tests run against `blogforge_test` (same Postgres driver as prod). No LLM key required — tests use the stub provider.

```bash
uv run pytest
```

## Project layout

- `src/blogforge/` — the package (`api/`, `config/`, `db/`, `domain/`, `graph/`, `llm/`, `templates/`)
- `tests/unit/`, `tests/integration/`
- `alembic/` — migrations
- `spec/` — product + engineering spec (read before modifying the app)
- `reports/sessions/` — per-session build logs

## Environment variables (see [.env.example](.env.example))

| Variable | Purpose |
|---|---|
| `BLOGFORGE_DATABASE_URL` | Postgres URL |
| `BLOGFORGE_TEST_DATABASE_URL` | Test Postgres URL (default: local `blogforge_test`) |
| `BLOGFORGE_LLM_PROVIDER` | `stub` (default) or `gemini` |
| `BLOGFORGE_GEMINI_API_KEY` | Required when provider is `gemini` |
| `BLOGFORGE_LLM_MODEL` | Default `gemini-2.5-flash` |
| `PORT` | Default `8001` |
