# Data Analyst Agent

A browser-based conversational data analyst agent. Upload CSV/Excel files and ask questions in plain English — the agent generates SQL via DuckDB, executes it, and returns formatted markdown tables with analyst narrative, powered by Gemini 2.5 Flash.

> **All commands in this README run from the repo root** (`/Users/sai/Workspace/Code/exp1` or wherever you cloned this repo).

## Stack

- Python 3.11+ · FastAPI · DuckDB · SQLite · Gemini 2.5 Flash (`google-genai` SDK)
- Single-page HTML/JS frontend (no build step)

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set:
```
DA_GEMINI_API_KEY=your-gemini-api-key-here
```

Or if your `.env` already has the bare `GEMINI_API_KEY=...` (from a previous setup), that works too — the app falls back to reading it.

### 3. Apply database migrations

```bash
uv run alembic upgrade head
```

Verify the migration was applied (should show a revision hash, not blank output):
```bash
uv run alembic current
```

### 4. Run the server

```bash
uv run python -m data_analyst
```

Open `http://localhost:8001` in your browser.

## Tests

All tests run against the real Gemini API using the key from `.env`. No mocking.

```bash
# Unit tests only (no Gemini API calls)
uv run pytest tests/unit/ -v

# Full suite (unit + integration + e2e, real Gemini API)
uv run pytest -v
```

## Usage

1. Open `http://localhost:8001`
2. Upload a CSV or Excel file using the sidebar
3. Ask questions in the chat panel
4. The agent generates SQL, executes it via DuckDB, and returns a formatted response

## Key features

- Natural language to SQL via Gemini tool-use (SELECT-only; destructive SQL refused)
- DuckDB in-process query engine (fast, zero config)
- Persistent sessions and dataset catalogue (SQLite)
- Append-only audit log (timestamp, question, SQL, datasets touched, latency, sql_error)
- Token economy: schema-aware table selection, history windowing, conversation summarisation
- Uploads survive server restarts (re-registered from SQLite catalogue on startup)

## Project layout

```
src/data_analyst/        Python package
  api/                   FastAPI routers
  agent/                 Gemini tool-use loop
  db/                    SQLAlchemy models and session
  config/                Settings (pydantic-settings)
  duckdb_service.py      DuckDB singleton
  domain/schemas.py      Pydantic response schemas
src/static/index.html    Single-page frontend (served at /)
tests/
  unit/                  No LLM calls
  integration/           Real Gemini API
  e2e/                   Golden-path + restart simulation
data/                    Uploaded files, SQLite DB, DuckDB file (gitignored)
```

## What's deferred (v2)

- Charts and dashboards
- Multi-user / authentication
- Multi-sheet Excel support
- Docker deployment
- Streaming responses
