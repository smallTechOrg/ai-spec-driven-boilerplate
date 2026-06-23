# Senior Data Analyst Agent

> **All commands in this README run from the repo root.**

A web-based AI data analyst: upload CSV, Excel, or JSON datasets, ask questions in plain English, and get rich responses — markdown narrative, sortable tables, and Chart.js charts — backed by real DuckDB SQL and Gemini 2.5 Flash.

## What It Does

- Upload structured datasets (CSV, Excel .xlsx, JSON) per session
- Ask natural-language questions — Gemini 2.5 Flash translates to DuckDB SQL
- Get rich responses: markdown text + sortable data table + auto-selected bar/line/pie chart
- Sessions persist across page reloads (SQLite-backed)
- Every SQL query logged with timestamp, SQL text, dataset name, row count, and latency
- Schema-only context injection — raw data rows never sent to the LLM

## Quick Start

### 1. Prerequisites

- Python 3.12+ and `uv` (`pip install uv`)
- Node.js 18+ and `pnpm` (`npm i -g pnpm`)

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env: set AGENT_GEMINI_API_KEY=<your Gemini API key>
# AGENT_DATABASE_URL defaults to sqlite:///./data/analyst.db
```

### 3. Install Python dependencies

```bash
uv sync
```

### 4. Run database migrations

```bash
uv run alembic upgrade head
uv run alembic current
```

`alembic current` must show a revision hash (e.g. `0002 (head)`). Blank output means the migration did not run.

### 5. Build the frontend

```bash
cd frontend && pnpm install && pnpm build && cd ..
```

### 6. Start the server

```bash
uv run python -m src
```

The server starts on `http://localhost:8001`.

### 7. Open the UI

Open `http://localhost:8001/app/` in your browser.

## Testing

```bash
# Phase 1 gate tests (no LLM key required)
uv run pytest tests/phase1/ -q

# Unit tests only (no LLM key required)
uv run pytest tests/unit/ -q

# All tests (requires AGENT_GEMINI_API_KEY in .env for LLM tests)
uv run pytest tests/ -q
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| POST | `/sessions` | Create a new analyst session |
| GET | `/sessions` | List all sessions |
| GET | `/sessions/{id}` | Get session with datasets + messages |
| POST | `/datasets` | Upload a dataset file (multipart) |
| GET | `/datasets?session_id=...` | List datasets for a session |
| GET | `/chat?session_id=...&q=...` | SSE stream: NL question → rich response |
| GET | `/audit?session_id=...` | Query audit log for a session |
| GET | `/app/` | Web UI (static Next.js export) |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_GEMINI_API_KEY` | Yes | — | Gemini API key |
| `AGENT_DATABASE_URL` | No | `sqlite:///./data/analyst.db` | SQLite database path |
| `AGENT_LLM_MODEL` | No | `gemini-2.5-flash` | Gemini model name |
| `PORT` | No | `8001` | Server port |

## Stack

- **Backend:** Python 3.12 + FastAPI + LangGraph + google-genai (Gemini 2.5 Flash) + DuckDB + SQLite/SQLAlchemy + Alembic
- **Frontend:** Next.js 15 + React 19 + Tailwind CSS v4 + Chart.js
- **Managed by:** `uv` (Python) + `pnpm` (frontend)

## Project Layout

```
src/                 ← Python package (FastAPI + LangGraph agent)
  api/               ← FastAPI routers (sessions, datasets, chat, audit)
  config/            ← Pydantic settings (AGENT_ prefix)
  db/                ← SQLAlchemy models + DuckDB loader
  domain/            ← Pydantic domain models
  graph/             ← LangGraph analyst graph (nodes, edges, state, runner)
  llm/               ← LLM client + Gemini provider
  prompts/           ← System prompt (analyst.md)
frontend/            ← Next.js static export (served at /app)
tests/
  unit/              ← no LLM key needed
  integration/       ← requires AGENT_GEMINI_API_KEY
  phase1/            ← Phase 1 gate tests
data/uploads/        ← uploaded dataset files (gitignored)
spec/                ← agent spec
alembic/             ← DB migrations
```

## Phase Status

- **Phase 1** — All 6 capabilities live: dataset upload, NL querying, rich responses, sessions, audit log, token economy
- **Phase 2** — Audit log UI viewer + session rename/delete (stubs in Phase 1 UI)
