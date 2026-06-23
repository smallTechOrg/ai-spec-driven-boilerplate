# Architecture

## System Overview

The Data Analyst Agent is a single-origin web application: a FastAPI backend (port 8001) serves both the REST API and the statically-exported Next.js frontend (mounted at `/app`). The user's browser is the only client. When a user uploads a file, FastAPI parses it with pandas and loads it into a session-namespaced SQLite table. When the user asks a question, a LangGraph agent sends schema context to Gemini 2.5 Flash via structured tool-use, receives a SQL string back, executes it against SQLite, logs the operation to the audit_log table, and returns a formatted markdown + table response. No DuckDB, no external database, no filesystem dataset storage beyond the SQLite DB file.

## Component Map

```
Browser
  │
  │  GET  /app/*              (static Next.js export)
  │  POST /datasets/upload    (multipart — X-Session-ID header)
  │  GET  /datasets           (X-Session-ID header)
  │  POST /query              (JSON body — X-Session-ID header)
  │  GET  /audit              (X-Session-ID header)
  │  GET  /health
  ▼
FastAPI  (port 8001)
  ├── StaticFiles → frontend/out/   (mounted at /app)
  ├── DatasetsRouter
  │     └── ingest/parser.py  ──► ingest/loader.py ──► SQLite (dynamic tables)
  ├── QueryRouter
  │     └── LangGraph Analyst Graph
  │           ├── query_planner  ──► Gemini 2.5 Flash (generate_sql tool, forced)
  │           ├── sql_executor   ──► SQLite (dynamic table, raw text() query)
  │           ├── response_formatter
  │           └── audit_logger   ──► SQLite (audit_log table)
  └── AuditRouter              ──► SQLite (audit_log table, read-only)
```

## Data Flow

### File Upload Flow

1. Browser POSTs multipart file + `X-Session-ID` header to `POST /datasets/upload`.
2. FastAPI validates file extension (`.csv` or `.xlsx`) and row count (≤ 500,000 rows; reject 422 otherwise).
3. `ingest/parser.py` reads the file into a pandas DataFrame; infers column names and types.
4. `ingest/loader.py` calls `DataFrame.to_sql()` with the session-namespaced table name (`{session_id_underscored}_{sanitized_filename}`) into the SQLite DB, `if_exists='replace'`.
5. A `datasets` row is inserted recording table_name, original_filename, row_count, column_names (JSON list), session_id. The metadata is returned to the browser.

### NL Query Flow

1. Browser POSTs `{question, dataset_table}` + `X-Session-ID` header to `POST /query`.
2. FastAPI validates that `dataset_table` starts with the requesting session's prefix (403 otherwise). Invokes the LangGraph analyst graph.
3. Graph executes:
   a. **query_planner** — runs `PRAGMA table_info({dataset_table})` on SQLite to fetch schema; builds a schema-context string; calls Gemini 2.5 Flash with `generate_sql` tool forced (tool_config mode=ANY); extracts the SQL string from the tool call. Retries up to 3× on Gemini error.
   b. **sql_executor** — executes the SQL via `sqlalchemy.text()` against SQLite; caps results at 1,000 rows; records duration_ms.
   c. **response_formatter** — assembles markdown answer text and a list-of-dicts table; falls back gracefully on empty results or null values.
   d. **audit_logger** — writes one `audit_log` row (session_id, dataset_table, question, sql_generated, row_count, duration_ms, error); non-fatal if write fails.
4. FastAPI returns `{answer, table, sql, audit_id}` as JSON, or `{error}` on 502.

## Session Isolation

Every dataset table in SQLite is named `{session_id_underscored}_{sanitized_name}`, where `session_id_underscored` is the session UUID with hyphens replaced by underscores. `POST /query` validates that the `dataset_table` field in the request body starts with the calling session's prefix before executing any SQL — a mismatch returns 403. The `sessions`, `datasets`, and `audit_log` ORM tables are filtered by `session_id` on every read. No authentication is used; isolation is enforced solely by this naming convention and API-layer validation.

## Frontend Serving

The Next.js frontend is built with `output: 'export'` and `basePath: '/app'` set in `next.config.js`. The static output lands in `frontend/out/`. FastAPI mounts this directory with `StaticFiles(directory="frontend/out", html=True)` at the path `/app`. All API calls from the frontend use relative paths (e.g. `/datasets/upload`) — single-origin, no CORS configuration needed.

> **Assumed:** The frontend is always built before starting the server in the test/handoff path (`pnpm build` then `uv run python -m src`). The `frontend/out/` directory must exist at server startup.

## Stack

> Concrete technology choices for this project. Generic every-project rules live in `harness/patterns/tech-stack.md`.

- **Language:** Python 3.12+
- **Agent framework:** LangGraph — StateGraph with prompt-chaining + tool-use + exception-handling pattern
- **LLM provider + model:** Google Gemini via `google-genai` SDK; model `gemini-2.5-flash` (configurable via `AGENT_LLM_MODEL`)
- **Backend:** FastAPI 0.115+
- **Database + ORM:** SQLite + SQLAlchemy 2.0 Mapped types + Alembic migrations; DB file at `./data/agent.db` (configurable via `AGENT_DATABASE_URL`)
- **Frontend:** Next.js 15 + React 19, static export (`output: 'export'`), `basePath: '/app'`, mounted by FastAPI StaticFiles at `/app`
- **Styling:** Tailwind CSS v4 with `postcss.config.mjs` (`@tailwindcss/postcss` plugin)
- **Dependency management:** `uv` (Python) + `pnpm` (frontend)

| Key library | Version | Purpose |
|-------------|---------|---------|
| `langgraph` | ≥0.1 | Agent graph orchestration |
| `google-genai` | ≥2.9.0 | Gemini API client |
| `sqlalchemy` | ≥2.0 | ORM + raw text() queries against SQLite |
| `alembic` | ≥1.13 | Database migrations |
| `pandas` | ≥2.0 | CSV/Excel parsing and DataFrame.to_sql() ingestion |
| `openpyxl` | ≥3.1 | Excel (.xlsx) backend for pandas read_excel |
| `python-multipart` | ≥0.0.9 | FastAPI UploadFile multipart form parsing |
| `structlog` | ≥24.1 | Structured logging |
| `pytest` | ≥8.0 | Test runner |
| `httpx` | ≥0.27 | Async test client for FastAPI |

**Avoid:**
- Any DuckDB dependency — all SQL runs against SQLite via SQLAlchemy.
- Storing uploaded files on the filesystem — data lives in SQLite dynamic tables only.
- Replacing SQLite with PostgreSQL — this is a fully-local single-user tool.
- Raw `sqlite3` module — use SQLAlchemy `text()` for all queries so parameterisation is consistent.
- `pnpm dev` as the handoff path — single-origin path is `pnpm build` + `uv run python -m src` + `http://localhost:8001/app/`.

> **Assumed:** Excel files are read with `pandas.read_excel(openpyxl)` and ingested via `DataFrame.to_sql()` into SQLite, the same path as CSV. No intermediate file storage.

> **Assumed:** `data/` directory is created at application startup if it does not exist.
