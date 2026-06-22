# Architecture

## System Overview

The Data Analyst Agent is a single-server web application. A browser-based single-page frontend communicates with a FastAPI backend over HTTP. The backend owns four concerns: file ingestion (storing uploads on disk and registering them as DuckDB tables), a conversational agent loop (Gemini tool-use to translate NL questions into SQL, execute them, and synthesise a markdown response), SQLite persistence (dataset catalogue, sessions, conversation history, audit log), and static file serving for the frontend. There are no external microservices; all processing is in-process.

## Component Map

```
Browser (HTML/JS SPA)
        │  HTTP (multipart upload / JSON REST / fetch)
        ▼
FastAPI Application  (port 8001)
  ├── Upload Router        → writes file to data/uploads/, triggers DuckDB registration
  ├── Dataset Router       → CRUD on dataset catalogue (SQLite)
  ├── Chat Router          → drives the Agent Loop per session
  ├── Session Router       → read session history from SQLite
  ├── Health Router        → liveness check
  └── Static File Mount    → serves src/static/index.html
        │
        ├── Agent Loop  (src/data_analyst/agent/)
        │     ├── runner.py        → run_turn() entry point: orchestrates Steps 1–7
        │     ├── loop.py          → Gemini tool-use loop (Steps 3–4)
        │     ├── tools.py         → tool implementations + destructive-SQL guard
        │     └── prompts.py       → SYSTEM_PROMPT constant; schema-selection prompt
        │
        ├── DuckDB Service  (src/data_analyst/duckdb_service.py)
        │     └── DuckDBService    → singleton connection + threading.Lock
        │                            re-registers tables from SQLite on startup
        │
        └── SQLite via SQLAlchemy  (src/data_analyst/db/)
              ├── models.py        → Dataset, Session, ConversationTurn, AuditLog
              └── session.py       → engine + sessionmaker + init_db (WAL mode)
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| HTTP / Routing | FastAPI routers; request validation (Pydantic); multipart file handling |
| Agent Loop | Context assembly, Gemini tool-use conversation, tool dispatch, response synthesis |
| Tool Execution | DuckDB SQL execution; catalogue reads; destructive-SQL guard |
| Persistence | SQLAlchemy ORM over SQLite: catalogue, sessions, conversation history, audit log |
| File Storage | Uploaded files stored at `data/uploads/<dataset_id>.<ext>`; never deleted |
| Frontend | Vanilla HTML/JS SPA served as static files from `src/static/`; no build step |

## Data Flow

### Upload flow
1. User selects a CSV or Excel file in the browser and submits the upload form.
2. FastAPI Upload Router receives the multipart request, saves the file to `data/uploads/`, generates a `dataset_id` (UUID).
3. The file is opened with pandas/openpyxl to infer the schema (column names, types) and count rows.
4. A row is inserted into the SQLite `datasets` table (name, description, schema JSON, row_count, file_path, upload_timestamp).
5. The DuckDB Engine registers the file as a named table (`CREATE OR REPLACE VIEW <name> AS SELECT * FROM read_csv_auto(...)` or equivalent for Excel via `INSTALL spatial` or pandas intermediary).
6. The API returns the dataset metadata to the browser; the sidebar refreshes.

### Chat flow
1. User types a question in the chat input and presses Send.
2. FastAPI Chat Router receives `{session_id, message}`, loads or creates the session from SQLite.
3. Context Builder identifies which datasets are relevant (Gemini sub-call if >5 datasets, else all schemas), fetches their schemas from SQLite.
4. Agent Loop calls Gemini 2.0 Flash with: compact system prompt + last N conversation turns (or summary) + relevant schemas + tool definitions.
5. Gemini returns one or more function-call blocks (`execute_sql`, `list_tables`, `describe_table`, `get_sample_rows`).
6. Tool Dispatcher executes each tool call; results are appended to the Gemini conversation.
7. Gemini synthesises a final text response (markdown table + narrative).
8. The turn (user message + assistant response) is appended to `conversation_turns` in SQLite.
9. If total turns > MAX_HISTORY_TURNS, the oldest turns are summarised and replaced with a summary entry.
10. An audit log entry is written to SQLite (if any SQL was executed).
11. The API returns `{response_markdown, session_id, generated_sql, datasets_touched, row_count_returned, latency_ms}` to the browser.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Gemini API (`gemini-2.0-flash`) | NL→SQL translation, response synthesis, clarification | Return HTTP 502 to client with user-visible error; log full error; do not retry automatically |
| DuckDB (in-process) | SQL execution over uploaded files | SQL errors returned as structured error to LLM (tool result); user sees error narrative |
| SQLite (local file `data/analyst.db`) | Catalogue, sessions, conversation history, audit log | Fatal startup error if DB file is unreadable; runtime write errors logged and surfaced to client |
| Local filesystem (`data/uploads/`) | Persistent file storage | Upload fails with 500 if disk is full or directory is unwritable; existing files are never deleted |

## DuckDB Connection Management

A singleton `DuckDBService` instance is created once at FastAPI startup via the lifespan handler. It holds:

- A single DuckDB connection opened against `data/duckdb.db` (file-backed, not `:memory:`). File-backed ensures that the DuckDB catalog survives within a process restart without re-registering tables, though tables are always re-registered from SQLite on startup to handle the case where the DuckDB file is missing or stale.
- A `threading.Lock` (`_lock`) acquired for every DuckDB operation (register, query, health-check). DuckDB supports concurrent reads on the same connection but the lock prevents races during the write phase of `CREATE OR REPLACE VIEW` registrations.

**Startup sequence:**
1. `init_db()` runs Alembic migrations / `Base.metadata.create_all` against SQLite.
2. `DuckDBService.startup()` opens the DuckDB connection and calls `register_all_datasets()`.
3. `register_all_datasets()` queries SQLite for all `datasets` rows where `is_active = true`, then issues a `CREATE OR REPLACE VIEW <table_name> AS SELECT * FROM read_csv_auto('<file_path>')` (or the Excel equivalent) for each. Failures per-dataset are logged and the dataset is skipped; the server still starts.

**Excel file handling:** Excel files (`.xlsx`, `.xls`) are converted to a temporary CSV by pandas at registration time and the view is pointed at the CSV. The temporary CSV lives at `data/uploads/<dataset_id>.csv` alongside the original. This avoids a DuckDB dependency on `openpyxl` at query time.

## Stack

- **Language:** Python 3.11+
- **Agent framework:** Custom single-agent tool-use loop (no LangGraph or CrewAI). Pattern: Tool Use (Pattern 5) from `harness/patterns/agentic-ai.md`, with Memory Management (Pattern 8) for cross-turn session history and Resource-Aware Optimization (Pattern 16) for schema selection and history windowing.
- **LLM provider + model:** Google Gemini 2.0 Flash via `google-genai` Python SDK (package: `google-genai`). Key: `GEMINI_API_KEY` from `.env`. Model configured via env var `LLM_MODEL`, default `gemini-2.0-flash`.

  > **Assumed:** The intake spec binds `gemini-2.0-flash`. The harness `tech-stack.md` notes that as of 2026 `gemini-2.5-flash` is the recommended safe default (2.0-flash may be restricted for new users). If the API returns a 404/model-not-found error, the operator should set `LLM_MODEL=gemini-2.5-flash` in `.env` without a code change.

- **Backend:** FastAPI 0.115+ + Uvicorn (ASGI). Dev port: **8001** (not 8000, per harness rule).
- **Database + ORM:**
  - SQLite (production persistence) via SQLAlchemy 2.0 with `Mapped`/`mapped_column` declarative ORM. WAL journal mode enabled at startup for concurrent reads+writes. DB file: `data/analyst.db`.
  - DuckDB 1.x (in-process query engine). Package: `duckdb`. Direct Python API — no ORM. File: `data/duckdb.db`.
  - **This project uses SQLite as its production database.** All harness references to "SQLite as a test substitute for PostgreSQL" do NOT apply here. Tests use an isolated SQLite DB created via `tmp_path` (the same driver as production).
- **Frontend:** Vanilla HTML/JS single-page app. No build step. File: `src/static/index.html`. Served by FastAPI `StaticFiles` mount at `/`. Markdown rendering via `marked.js` (CDN).
- **Dependency management:** `uv` + `pyproject.toml`. All dependencies in `[project.dependencies]`; dev tools (pytest, etc.) in `[dependency-groups.dev]`.
- **File uploads:** FastAPI multipart. Max 200 MB enforced by FastAPI request size limit. Stored under `data/uploads/`.
- **Migrations:** Alembic 1.x targeting SQLite. `alembic.ini` at repo root. Migration script generated by `uv run alembic revision --autogenerate -m "initial"`.

**Key library versions (pinned in pyproject.toml):**

| Library | Version | Purpose |
|---------|---------|---------|
| `fastapi` | `>=0.115,<1` | HTTP framework + routing |
| `uvicorn[standard]` | `>=0.30` | ASGI server |
| `sqlalchemy` | `>=2.0,<3` | ORM over SQLite |
| `alembic` | `>=1.13` | DB migrations |
| `google-genai` | `>=1.0` | Gemini API client |
| `duckdb` | `>=1.0` | In-process SQL engine |
| `pandas` | `>=2.0` | CSV/Excel schema inference + Excel→CSV conversion |
| `openpyxl` | `>=3.1` | Excel file reading (pandas dependency) |
| `pydantic` | `>=2.0` | Request/response models |
| `pydantic-settings` | `>=2.0` | Settings with env-file support |
| `python-multipart` | `>=0.0.9` | FastAPI multipart upload support |
| `pytest` | `>=8.0` | Test runner (dev dependency) |
| `pytest-asyncio` | `>=0.23` | Async test support (dev dependency) |
| `httpx` | `>=0.27` | FastAPI TestClient (dev dependency) |
| `python-dotenv` | `>=1.0` | `.env` loading in tests |

**Avoid:** ORMs or query builders for DuckDB — use the `duckdb` Python package directly. Do not use LangChain or LangGraph. Do not use React, Vue, or any JS framework requiring a build step.

## Deployment Model

Local development server: `uv run python -m data_analyst` (binds to port **8001**). Single process. No Docker for v1. SQLite database at `data/analyst.db`; DuckDB at `data/duckdb.db`; uploads at `data/uploads/`. All three paths created on startup if absent. The `PORT` env var overrides the default port.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `LLM_MODEL` | No | `gemini-2.0-flash` | Gemini model ID (override for availability) |
| `DATABASE_URL` | No | `sqlite:///data/analyst.db` | SQLAlchemy DB URL |
| `DUCKDB_PATH` | No | `data/duckdb.db` | DuckDB file path |
| `UPLOAD_DIR` | No | `data/uploads` | Directory for uploaded files |
| `MAX_HISTORY_TURNS` | No | `20` | Turns before summarisation triggers |
| `SUMMARY_KEEP_TURNS` | No | `6` | Turns to keep after summarisation |
| `MAX_TOOL_ROUNDS` | No | `10` | Max tool-call rounds per agent turn |
| `PORT` | No | `8001` | HTTP server port |
| `LOG_LEVEL` | No | `INFO` | Logging level |

`.env.example` must include all of the above with placeholder values. `GEMINI_API_KEY` is the only value the operator must fill in manually (requested at intake).

## Project Layout

```
<repo root>
├── src/
│   ├── data_analyst/                   ← Python package
│   │   ├── __init__.py                 ← __version__ = "0.1.0"
│   │   ├── __main__.py                 ← uvicorn.run(app, host="0.0.0.0", port=PORT)
│   │   ├── api/
│   │   │   ├── __init__.py             ← create_app() factory + lifespan
│   │   │   ├── _common.py              ← ok(), api_error()
│   │   │   ├── datasets.py             ← POST /datasets, GET /datasets, DELETE /datasets/{id}
│   │   │   ├── chat.py                 ← POST /chat
│   │   │   ├── sessions.py             ← GET /sessions/{session_id}/history
│   │   │   └── health.py               ← GET /health
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── runner.py               ← run_turn(session_id, message) → TurnResult
│   │   │   ├── loop.py                 ← gemini_tool_loop(messages, tools) → final text
│   │   │   ├── tools.py                ← tool implementations + destructive-SQL guard
│   │   │   └── prompts.py              ← SYSTEM_PROMPT, schema_selection_prompt()
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py             ← Pydantic BaseSettings (env prefix DA_)
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py               ← Dataset, Session, ConversationTurn, AuditLog
│   │   │   └── session.py              ← engine + sessionmaker + init_db (WAL)
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py              ← Pydantic request/response schemas
│   │   └── duckdb_service.py           ← DuckDBService singleton + table management
│   └── static/
│       └── index.html                  ← single-page app (HTML + inline JS)
├── tests/
│   ├── conftest.py                     ← settings reset + isolated SQLite DB fixture
│   ├── unit/
│   │   ├── test_smoke.py               ← import package; assert __version__
│   │   ├── test_duckdb_service.py      ← register CSV, execute SELECT, error paths
│   │   ├── test_destructive_guard.py   ← guard rejects DROP/DELETE/TRUNCATE/ALTER
│   │   ├── test_models.py              ← SQLAlchemy round-trip: insert + query
│   │   └── test_audit_log.py           ← audit entry written; failure is non-fatal
│   ├── integration/
│   │   ├── test_upload.py              ← POST /datasets → file on disk + SQLite row + DuckDB view
│   │   ├── test_chat.py                ← upload → POST /chat → audit entry; real Gemini
│   │   └── test_session.py             ← session persist + history endpoint
│   └── e2e/
│       └── test_golden_path.py         ← upload CSV → 3 questions → restart sim → session intact
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
├── data/                               ← created at runtime; gitignored
│   ├── analyst.db
│   ├── duckdb.db
│   └── uploads/
├── spec/
├── reports/
├── harness/
├── pyproject.toml
├── alembic.ini
├── .env.example
├── .gitignore
└── README.md
```

**Notes on deviations from the harness canonical layout:**
- `graph/` is replaced by `agent/` (no LangGraph; custom tool-use loop).
- `src/static/` holds the frontend HTML/JS (all application files under `src/`).
- `llm/` directory is omitted; the Gemini client is instantiated directly in `agent/loop.py` (single provider, no abstraction layer needed).
- `tools/` at the package level is replaced by `agent/tools.py` (tools are tightly coupled to the agent loop and DuckDB service).
- `domain/schemas.py` replaces per-entity files in `domain/` (Pydantic schemas are few and simple).
