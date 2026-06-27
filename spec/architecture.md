# Architecture

## System Overview

A personal data analysis agent that lets a single user upload CSV or Excel files, ask plain-English questions about the data, and instantly receive an interactive chart (bar, line, or scatter) plus a written summary — all in the browser. The system runs entirely locally: FastAPI backend with LangGraph orchestration and SQLite storage, serving a Next.js static export at `/app/`. Pandas handles all full-data computation locally; Gemini receives only the column schema and up to 20 sample rows.

## Component Map

```
[Browser (Next.js static export at /app/)]
    ↓ HTTP fetch (same origin, port 8001)
[FastAPI Backend (src/api/)]
    ↓ invokes
[LangGraph Runner (src/graph/)]
    ↓ analyze_data node
[pandas — reads full file from data/uploads/]  [Gemini 2.5 Pro — receives schema + 20 rows only]
    ↓ results merged
[SQLite (datasets + runs tables)]
    ↓ file references
[data/uploads/ — stored CSV/Excel files]
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API (src/api/) | HTTP routing, multipart file upload, request/response validation, envelope formatting |
| Graph (src/graph/) | LangGraph StateGraph wiring — nodes, conditional edges, entry point, compilation |
| Nodes (src/graph/nodes.py) | `analyze_data`: load DataFrame, build prompt, call Gemini, execute pandas code, return chart JSON |
| LLM (src/llm/) | Gemini 2.5 Pro client via google-genai SDK; prompt loading from src/prompts/ |
| Domain (src/domain/) | Dataset parsing logic (schema extraction, sample rows); analysis result models |
| DB (src/db/) | SQLAlchemy 2.0 models (Dataset, Run); SQLite session factory; Alembic migrations |
| Config (src/config/) | Pydantic Settings with AGENT_ prefix; env var loading from .env |
| Frontend (frontend/) | Next.js 15 static export; React 19 components; Recharts charts; Tailwind CSS v4 |

## Data Flow

1. User drags a CSV or Excel file onto the dropzone
2. Frontend POSTs to `/datasets` (multipart) → backend parses with pandas, stores file at `data/uploads/{dataset_id}_{filename}`, inserts dataset row into SQLite with columns_json, sample_rows_json (first 20 rows), and row_count
3. Frontend receives `{ dataset_id, filename, columns, row_count }` and shows column list + row count
4. User types a question and clicks Analyze
5. Frontend POSTs to `/analyze` with `{ dataset_id, question }`
6. FastAPI creates a Run record (status="running") and invokes the LangGraph graph
7. `analyze_data` node reads dataset row from SQLite, loads full DataFrame from `file_path` using pandas
8. Node builds prompt: column schema + first 20 sample rows as CSV text + user question — this is ALL Gemini receives
9. Node calls Gemini 2.5 Pro → receives JSON: `{ pandas_code, chart_type, labels, values, summary }`
10. Node executes `pandas_code` in restricted namespace `{"df": df, "pd": pd}` → reads `namespace["result"]["labels"]` and `namespace["result"]["values"]`
11. Gemini's illustrative labels/values are discarded; real computed values are used
12. Node sets `chart_type`, `labels`, `values`, `summary` in AgentState
13. `finalize` node updates Run record to status="completed"
14. FastAPI returns `{ chart_type, labels, values, summary, dataset_id }` to the browser
15. Frontend renders Recharts chart + summary card

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|-------------|
| Gemini 2.5 Pro API (google-genai) | NL understanding, pandas code generation, chart type selection, summary writing | HTTP 500 from backend; frontend shows error card |
| SQLite (local file) | Dataset metadata, Run history | Application fails to start; error surfaced at startup |
| Local filesystem (data/uploads/) | Stored CSV/Excel files | Upload fails with 500; clear error shown to user |

## Stack

> This project's concrete technology choices captured at intake.

- **Language:** Python 3.12
- **Agent framework:** LangGraph 0.1+ (StateGraph with conditional edges)
- **LLM provider + model:** Google Gemini 2.5 Pro via google-genai SDK; model name `gemini-2.5-pro`, configurable via `AGENT_LLM_MODEL` env var
- **Backend:** FastAPI 0.115+
- **Database + ORM:** SQLite + SQLAlchemy 2.0; Alembic for migrations
- **Frontend:** Next.js 15 (App Router, `output: 'export'`, `basePath: '/app'`), React 19, Recharts ^2.12, Tailwind CSS v4
- **Dependency management:** uv + pyproject.toml (Python); pnpm 9+ (frontend)

| Key library | Version | Purpose |
|-------------|---------|---------|
| google-genai | >=2.9.0 | Gemini API client |
| langgraph | >=0.1 | LangGraph graph orchestration |
| pandas | >=2.2 | CSV/Excel parsing, schema extraction, pandas_code execution |
| openpyxl | >=3.1 | Excel (.xlsx/.xls) file support for pandas |
| fastapi | >=0.115 | HTTP API framework |
| sqlalchemy | >=2.0 | ORM + SQLite session management |
| alembic | >=1.13 | Database migrations |
| pydantic-settings | >=2.0 | Settings with AGENT_ prefix, .env loading |
| recharts | ^2.12 | Recharts chart components (frontend) |
| @tailwindcss/postcss | ^4.0 | Tailwind CSS v4 PostCSS plugin (frontend) |

**Avoid:**
- `aiofiles` — nodes are synchronous; use standard file I/O
- `asyncio` inside LangGraph nodes — nodes must be sync functions
- Sending the full CSV/Excel content to Gemini — privacy and cost rule; only schema + 20 rows
- SQLite as a substitute for PostgreSQL in Phase 2 tests — Phase 2 tests must use the real PostgreSQL driver (`psycopg2-binary`)
- Running the frontend on port 3000 as the primary test path — the single-origin path (`uv run python -m src` + pre-built frontend at `/app/`) is canonical for testing

## Deployment Model

Local development server only. Single-origin run:

1. `cd frontend && pnpm build` — builds Next.js static export to `frontend/out/`
2. `uv run python -m src` — starts FastAPI on port 8001; serves API at `/` and static frontend at `/app/`
3. User opens `http://localhost:8001/app/`

> **Assumed:** The FastAPI `__main__.py` mounts the Next.js static export from `frontend/out/` at the `/app` path using `StaticFiles`. This is the existing boilerplate pattern.
