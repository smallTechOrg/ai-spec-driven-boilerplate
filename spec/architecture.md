# Architecture

## System Overview

A fully-local, single-user data analysis tool. The user interacts through a browser-based chat UI. They upload CSV or Excel files, which are immediately parsed and stored as SQLite tables. They then ask natural-language questions; the backend agent graph generates SQL, executes it, computes statistics in Python, calls Gemini to produce a prose narrative, auto-selects chart types, and returns the full result to the UI. Everything runs on the user's machine; no data leaves it except for the prompt sent to the Gemini API.

---

## Component Map

```
Browser (Next.js static export at /app/)
    |
    | HTTP (fetch, multipart)
    v
FastAPI (port 8001)
    |
    |-- POST /sessions              → SessionRow in SQLite
    |-- POST /sessions/{id}/files   → pandas parse → SQLite table + UploadedFileRow
    |-- POST /sessions/{id}/analyze → LangGraph agent graph
    |                                     |
    |                                     ├─ generate_sql (Gemini API call)
    |                                     ├─ execute_sql  (SQLite)
    |                                     ├─ generate_insights (Gemini API call)
    |                                     └─ generate_charts  (pure Python)
    |-- GET  /sessions/{id}/files   → UploadedFileRow list from SQLite
    |-- GET  /runs/{run_id}         → RunRow from SQLite
    v
SQLite (WAL mode)
    |
    ├─ runs
    ├─ sessions
    ├─ uploaded_files
    ├─ analysis_cache
    └─ <dynamic upload tables>
```

---

## Layers

| Layer | Responsibility |
|-------|----------------|
| Frontend (Next.js) | Chat UI, file drop zone, inline chart rendering with Recharts |
| API (FastAPI) | HTTP routing, request validation (Pydantic), multipart file handling |
| Agent Graph (LangGraph) | Orchestrates generate_sql → execute_sql → generate_insights + generate_charts |
| LLM Client | Wraps google-genai; auto-selects Gemini when `AGENT_GEMINI_API_KEY` is set |
| Ingest Service | pandas parse → table name sanitization → SQLite `to_sql` |
| Cache Layer | SHA-256 keyed lookup in `analysis_cache` before running the graph |
| DB / ORM | SQLAlchemy 2.0 sync ORM + Alembic migrations for schema tables |

---

## Data Flow

### File Upload

1. Browser sends `POST /sessions/{id}/files` with multipart binary.
2. FastAPI reads the file bytes into memory (max 50 MB enforced by request size limit).
3. pandas reads bytes into a DataFrame (`read_csv` or `read_excel`).
4. Column names are sanitized; row count is validated (max 500 000).
5. DataFrame is written to SQLite via `df.to_sql(table_name, conn, if_exists="replace", index=False)`.
6. An `uploaded_files` row is upserted (DELETE + INSERT).
7. Response: `{table_name, row_count, columns}`.

### Analysis (question → result)

1. Browser sends `POST /sessions/{id}/analyze` with `{question}`.
2. FastAPI creates a `runs` row (`status=pending`), assembles the initial `AnalysisState`.
3. Cache check: compute `question_hash` and `table_hash`; if a matching `analysis_cache` row exists, copy its `result_json` into the `runs` row and return immediately.
4. Cache miss: invoke `agentic_ai.invoke(state)` — the LangGraph graph.
5. `generate_sql` node: build schema context (PRAGMA table_info for each session table + 20-row sample), call Gemini to generate SQL, validate with `EXPLAIN QUERY PLAN`.
6. `execute_sql` node: run the validated SELECT against SQLite; enforce 10 000-row cap.
7. `generate_insights` node: compute statistics in Python (no LLM call for empty result), then call Gemini to write the prose narrative.
8. `generate_charts` node: deterministic Python — select up to 4 chart types from data shape, build ChartSpec list (max 500 points each).
9. `finalize` node: write all result fields to the `runs` row and write to `analysis_cache`.
10. FastAPI returns the complete run result.

---

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Gemini API (`gemini-2.5-pro`) | SQL generation and prose narrative | `state.error` set; route to handle_error; run marked `failed` |
| SQLite (local file) | All structured data and dynamic upload tables | Fatal startup failure; logged to stderr |
| pandas | CSV/Excel parsing | HTTP 422 returned; no table created |

---

## Token Efficiency Strategy

- Schema context passed to Gemini for SQL generation: table name + column names + inferred types + up to **20 sample rows per table** (random sample). Total capped at the equivalent of 1 000 rows of serialized text.
- Statistics JSON passed to Gemini for prose generation: structured metrics JSON only — raw rows are never sent. If the JSON exceeds 4 000 tokens, truncate to the top 5 numeric columns by cardinality.
- Cache: `analysis_cache` avoids any Gemini call on a repeated question against the same tables.

---

## Stack

- **Language:** Python 3.12
- **Agent framework:** LangGraph 0.1+ (StateGraph with typed state, named nodes, conditional edges)
- **LLM provider + model:** Google Gemini via `google-genai>=2.9.0`; default model `gemini-2.5-pro` (env-configurable via `AGENT_LLM_MODEL`)
- **Backend:** FastAPI 0.115+ on port 8001; uvicorn[standard]
- **Database + ORM:** SQLite (WAL mode) + SQLAlchemy 2.0 sync ORM + Alembic migrations
- **Frontend:** Next.js 15, React 19, Tailwind v4 (`@tailwindcss/postcss`), pnpm; static export at `frontend/out/`, served by FastAPI at `/app/`
- **Dependency management:** uv + `pyproject.toml` (Python); pnpm (frontend)

| Key library | Version constraint | Purpose |
|-------------|--------------------|---------|
| `google-genai` | `>=2.9.0` | Gemini API client |
| `langgraph` | `>=0.1` | Agent graph orchestration |
| `fastapi` | `>=0.115` | HTTP API |
| `sqlalchemy` | `>=2.0` | ORM and raw SQL execution |
| `alembic` | `>=1.13` | DB migrations |
| `pandas` | `>=2.2` | CSV/Excel parsing and `to_sql` ingest |
| `openpyxl` | `>=3.1` | Excel file reading (pandas backend) |
| `pydantic` | `>=2.7` | Request/response validation and settings |
| `pydantic-settings` | `>=2.3` | `.env` loading with `extra="ignore"` |
| `structlog` | `>=24.1` | Structured logging |
| `recharts` | `^2.12` (npm) | Client-side chart rendering |
| `pytest` | `>=8.2` | Test runner |
| `httpx` | `>=0.27` | TestClient for API tests |

**Avoid:**
- Server-side chart image generation (no matplotlib/seaborn/plotly server renders) — charts are spec JSON returned to the client; Recharts renders them in-browser.
- `asyncio` / async SQLAlchemy in the agent graph — the existing skeleton uses sync SQLAlchemy; keep it sync to avoid two execution models.
- PostgreSQL in Phase 1-3 — SQLite only; PostgreSQL connectivity is Phase 4.

---

## Deployment Model

Local only. The user runs `uv run python -m src` from the repo root after `uv run alembic upgrade head` and `cd frontend && pnpm build`. The frontend static export and the API are served from one process on port 8001. No containerization, no cloud deployment, no authentication.

> **Assumed:** `pandas` and `openpyxl` must be added to `pyproject.toml` `[project.dependencies]` in the Phase 1 migration — they are not currently listed in the skeleton.
