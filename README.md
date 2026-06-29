# Local Data Analyst — CSV/Excel Analysis Agent

> **All commands run from the repo root** (this directory — where `pyproject.toml` and `alembic.ini` live). There is no subdirectory to `cd` into except the explicit `cd frontend` steps below.

A personal, **local-first** data-analysis agent. Upload a CSV, ask a question in plain English, and get an analyst answer with the **exact DuckDB SQL** behind every number.

**Hard privacy boundary:** a local DuckDB engine does all data crunching; the LLM (Gemini) only ever sees the schema, column names, and aggregate result rows — **never raw data rows**. Your data stays on your machine.

## Stack

Python 3.12 · FastAPI (`api:app` @ :8001) · LangGraph · DuckDB (compute) · SQLite (app state, SQLAlchemy 2.0 + Alembic) · Next.js static export at `/app/` · Gemini `gemini-3.1-pro` · uv.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python deps + runner)
- [pnpm](https://pnpm.io/) + Node ≥ 20 (frontend build)
- A Gemini API key in `.env` (copy `.env.example` → `.env`, set `AGENT_GEMINI_API_KEY`)

```bash
cp .env.example .env
# then edit .env and set AGENT_GEMINI_API_KEY=...
```

## Setup & run

```bash
# 1. Python dependencies
uv sync --extra dev

# 2. Build the frontend (static export served by the API at /app/)
cd frontend && pnpm install && pnpm build && cd ..

# 3. Create the database tables
uv run alembic upgrade head
uv run alembic current        # must print a revision (e.g. "0002 (head)"), not blank

# 4. Start the app
uv run python -m src
```

Then open **http://localhost:8001/app/** in your browser.

## Try it (Phase 1)

1. In the Upload panel, choose `samples/sales.csv` (a small sample is included) and click **Upload CSV**. The dataset summary (row count + columns) appears.
2. In the Question panel type **"What is the total revenue?"** and click **Ask**.
3. The Answer panel shows the plain-English answer, an **Exact SQL** block with the DuckDB query that produced it, and a small result table.

**What is real in Phase 1:** upload CSV → ask → answer with the exact SQL + result table.

**Clearly-labelled "Coming soon" stubs** (visible but not yet functional — not bugs): Datasets sidebar, Chart, Summary table, Profile panel, Follow-up chips, Cost meter, History/audit-trail browser, Live step stream. These are wired up in Phases 2–3.

## Tests

```bash
uv run pytest                       # backend: unit + real-Gemini integration (key from .env)
cd frontend && npx playwright test  # live UI E2E (requires the app running at :8001)
```

## How it works

The question runs through a LangGraph graph: `generate_sql → execute_sql → answer → finalize`, with a **retry-on-SQL-error** edge — a DuckDB error is fed back to the model so it corrects the query (bounded retries). Only schema + aggregate result rows are ever sent to Gemini; raw rows stay in the local per-dataset DuckDB file. Every run is persisted to SQLite as an audit trail.

## Configuration (`.env`)

| Var | Purpose | Default |
|-----|---------|---------|
| `AGENT_GEMINI_API_KEY` | Gemini API key (required) | — |
| `AGENT_LLM_MODEL` | Override model | `gemini-3.1-pro` |
| `AGENT_DATABASE_URL` | SQLite app DB | `sqlite:///./data/agent.db` |
| `PORT` | Server port | `8001` |
