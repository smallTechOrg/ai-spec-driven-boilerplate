# Architecture

---

## System Overview

A single-process, local-first FastAPI service that serves a Next.js static UI at `/app` and exposes a small JSON API. A user uploads a tabular file; the backend ingests it into a local **DuckDB** analytics database (the data store) and records its metadata in a **SQLAlchemy/SQLite** database (the metadata store). When the user asks a natural-language question, a **LangGraph** agent profiles the dataset's schema, asks the LLM (Gemini) to generate SQL from schema + tiny samples only, executes that SQL locally on DuckDB, and asks the LLM to narrate the result. Every operation is written to a persistent audit log. The only network egress is the Gemini call, which carries metadata (schema + capped samples/aggregates), never bulk rows.

## Component Map

```
                          Browser (Next.js static export @ /app)
                                       │  JSON over HTTP
                                       ▼
   ┌───────────────────────────── FastAPI (src/api) ─────────────────────────────┐
   │  datasets.py        ask.py            audit.py          health.py            │
   └───────┬───────────────┬──────────────────┬──────────────────────────────────┘
           │               │                  │
           ▼               ▼                  ▼
   ingest service    graph.runner        audit service
   (src/services)    (LangGraph)         (src/services)
           │               │                  │
           │               ▼                  │
           │     ┌─────────────────────────┐  │
           │     │ LangGraph agent (src/graph)
           │     │ profile_schema →        │  │        ┌──────────────────┐
           │     │ generate_sql ──LLM────► │──┼───────►│ Gemini API       │
           │     │ execute_sql  ──DuckDB►  │  │        │ (metadata only)  │
           │     │ narrate ──────LLM────►  │──┼───────►└──────────────────┘
           │     └─────────────────────────┘  │
           ▼               ▼                   ▼
   ┌──────────────────┐         ┌─────────────────────────────────┐
   │ DuckDB (data)    │         │ SQLAlchemy/SQLite (metadata)     │
   │ one table per    │         │ sessions, datasets, audit_logs   │
   │ dataset; rows    │         │ runs (skeleton)                  │
   └──────────────────┘         └─────────────────────────────────┘
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| **UI** (`frontend/`) | Upload, dataset list, ask box, narrative + table render, audit viewer/export, labelled stubs. |
| **API** (`src/api/`) | HTTP contract; request validation; `ok(data)` envelope; delegate to services/runner. |
| **Agent** (`src/graph/`) | LangGraph pipeline that turns an NL question into SQL → result → narrative. |
| **Services** (`src/services/`) | File ingestion into DuckDB, schema profiling, query execution, audit logging — all local. |
| **LLM** (`src/llm/`) | Provider abstraction (Gemini auto-detected from key); the only external call. |
| **Data stores** | DuckDB for dataset rows; SQLAlchemy/SQLite for metadata + audit. |

## Data Flow

1. **Trigger:** user uploads a file (`POST /datasets`) or asks a question (`POST /ask`) from the UI.
2. **Ingest** (upload): `ingest` service reads the CSV/Excel via pandas/openpyxl, writes a typed table into DuckDB (`AGENT_DUCKDB_PATH`), profiles the schema (column names, types, row count, capped per-column samples), and records a `DatasetRow` (linked to the active `SessionRow`) in metadata.
3. **Ask:** `runner` loads the dataset's schema profile from metadata, invokes the LangGraph agent.
4. **profile_schema** builds the token-economical context: column names + types + up to `AGENT_MAX_SAMPLE_ROWS` (default 5) sample rows and basic aggregates — never the full table.
5. **generate_sql** sends that context + the NL question to Gemini and gets back a single read-only SQL statement (validated against the dataset's columns; non-SELECT rejected).
6. **execute_sql** runs the SQL on DuckDB locally, capturing row count and duration; truncates the returned result set to a display cap for the UI.
7. **narrate** sends the question + the SQL + a capped preview of the result (not the full result) to Gemini for a short senior-analyst narrative.
8. **Audit:** an `AuditLogRow` is persisted (timestamp, session/dataset, nl_question, generated_sql, row_count, duration_ms, status).
9. **Output:** API returns `{ narrative, sql, columns, rows (capped), row_count, duration_ms }`; the UI renders narrative + table and appends to the audit view.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Gemini API | SQL generation + narration (metadata only) | `generate_sql`/`narrate` node sets `state["error"]`; run routes to `handle_error`, audit row marked `failed`, API returns 502 with a clear message. |
| DuckDB (embedded) | Local dataset storage + query execution | Query error sets `state["error"]`; audit row `failed`; API 400/500 with the DuckDB error message. |
| SQLite (embedded) | Metadata + audit persistence | Startup/migration failure is fatal; surfaced at boot. |

## Stack

> Concrete choices for this project. Generic rules (model-naming, DB driver, dev port, real-key tests) live in `harness/patterns/tech-stack.md`.

- **Language:** Python 3.12+ (backend); TypeScript (frontend).
- **Agent framework:** LangGraph — graph compiled at startup in `src/graph/agent.py`; nodes are `(state)->state`; `TypedDict` state; runner in `src/graph/runner.py`.
- **LLM provider + model:** Gemini, auto-detected from `AGENT_GEMINI_API_KEY`; default model `gemini-2.5-flash` (override via `AGENT_LLM_MODEL`). Existing `src/llm/providers/gemini.py`.
- **Backend:** FastAPI; package root is **`src/`** with `pythonpath = ["src"]` → top-level imports (`from graph.state import AgentState`, `from config.settings import get_settings`). No `src/agent/` subpackage.
- **Database + ORM:** SQLAlchemy 2.0 + Alembic over `AGENT_DATABASE_URL` (SQLite for local dev) for metadata; **DuckDB** (embedded) at `AGENT_DUCKDB_PATH` for dataset rows.
- **Frontend:** Next.js 15 + React 19, static export (`output: 'export'`, `basePath: '/app'`), served by FastAPI at `/app`; test URL `http://localhost:8001/app/` (single origin).
- **Dependency management:** uv + `pyproject.toml` (Python); pnpm (frontend).

| Key library | Version | Purpose |
|-------------|---------|---------|
| fastapi | >=0.115 | HTTP API (existing) |
| langgraph | >=0.1 | Agent graph (existing) |
| google-genai | >=2.9.0 | Gemini client (existing) |
| sqlalchemy | >=2.0 | Metadata ORM (existing) |
| alembic | >=1.13 | Migrations (existing) |
| **duckdb** | >=1.1 | Local analytics engine — **add** |
| **pandas** | >=2.2 | CSV/Excel ingestion — **add** |
| **openpyxl** | >=3.1 | Excel (.xlsx) reading — **add** |
| **python-multipart** | >=0.0.9 | FastAPI file upload parsing — **add** |

**Avoid:** Sending raw dataset rows to the LLM (token-economy violation). Cloud/warehouse drivers (local-only constraint). Arbitrary user SQL execution (only agent-generated read-only SQL). Substituting another DB for DuckDB or SQLite-for-PostgreSQL — the stack is locked.

## Deployment Model

Single long-running local process: `uv run python -m src` starts uvicorn on port 8001, serving the API and the pre-built static frontend from `frontend/out`. All state lives in local files: the SQLite metadata DB (`AGENT_DATABASE_URL`) and the DuckDB data file (`AGENT_DUCKDB_PATH`), both persisting across restarts.
