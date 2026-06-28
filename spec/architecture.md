# Architecture

System architecture for the Local Data Analyst agent.

---

## System Overview

The Local Data Analyst is a single-user, local long-running service. The user interacts through a single-page web workspace (Next.js static export served at `/app/`) that talks to a FastAPI backend over REST. The backend ingests CSV/Excel files into a local **DuckDB** query engine, profiles them, and answers plain-English questions through a **LangGraph** PLAN-THEN-EXECUTE agent. The agent drafts a multi-step plan, generates DuckDB SQL, runs that SQL **locally** against the user's data, aggregates the results, and only then sends **schema + aggregate numbers** (never raw rows) to **Gemini** (`gemini-2.5-flash`) to produce a plain-language narration with key stats, a chart spec, a summary table, and a written insight. Application state — the dataset library, conversation history, and a full audit trail of every run (question, plan, generated SQL, result summary, tokens, estimated cost) — lives in **SQLite** (SQLAlchemy 2.0 + Alembic). The defining architectural property is the **privacy boundary**: raw data rows never leave the machine.

## Component Map

```
[Browser: Next.js workspace at /app/]
        │  REST (JSON)
        ▼
[FastAPI app  (src/api)]
        │
        ├─► [Ingest + Profiler (src/data)] ──► [DuckDB engine (local files)]
        │                                            ▲
        ▼                                            │ local SQL only
[LangGraph PLAN-THEN-EXECUTE agent (src/graph)] ─────┘
        │            │
        │            └─► schema + AGGREGATES only ─► [Gemini gemini-2.5-flash (src/llm)]
        │                                              (NO raw rows cross this line)
        ▼
[SQLite app-state: library, history, audit (src/db, SQLAlchemy + Alembic)]
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| **Web UI** (`frontend/`) | Single-page workspace: upload, profile card, question box, rich-answer render, expandable code/steps/profile panel, cost display, labelled stubs. Static export served at `/app/`. |
| **API** (`src/api/`) | REST endpoints (`datasets`, `ask`, `runs`, `health`). Uses the `ok(data)`/`api_error()` envelope. Validates input, delegates to the graph/data layers, returns the rich-answer envelope. |
| **Agent graph** (`src/graph/`) | LangGraph PLAN-THEN-EXECUTE: profile → plan → local-execute → aggregate → narrate → suggest-follow-ups → finalize / handle_error. Owns `AgentState`. |
| **Data engine** (`src/data/`) | Ingestion (CSV/Excel → DuckDB), profiling, the pure local DuckDB query runner, and cost estimation. The privacy boundary is implemented here: aggregates out, raw rows never out. |
| **LLM** (`src/llm/`) | Gemini provider + client; captures prompt/completion token counts per call. Default model `gemini-2.5-flash`. |
| **Persistence** (`src/db/`) | SQLite app-state via SQLAlchemy 2.0; Alembic migrations. Dataset library, conversation Messages, Run audit records. |
| **Observability** (`src/observability/`) | Structured logging; per-LLM-call token/cost capture surfaced into the Run record and the API response. |

## Data Flow

1. **Trigger:** the user uploads a CSV/Excel file via the workspace (`POST /api/datasets`). Each Excel sheet becomes its own dataset.
2. **Ingest:** the file is parsed and loaded into a local DuckDB table (CSV directly; Excel sheets via pandas/openpyxl). A `Dataset` row is written to SQLite.
3. **Profile:** the profiler runs local DuckDB queries to compute row count, column names/types, null counts, and basic per-column stats. The profile is returned to the UI and cached on the `Dataset` row.
4. **Ask:** the user submits `dataset_id` + a plain-English question (`POST /api/ask`). A `Run` row is created.
5. **Plan:** the LLM receives ONLY the schema + profile (no rows) and drafts a multi-step plan + the DuckDB SQL to run.
6. **Execute locally:** the generated SQL runs against DuckDB on the local machine. Raw result rows stay in memory locally.
7. **Aggregate:** results are reduced to summary numbers / small aggregate tables suitable for narration (the privacy boundary — only aggregates proceed).
8. **Narrate:** the LLM receives the schema + the aggregate numbers (never raw rows) and produces the plain-language answer, key stats, chart spec, summary table, and written insight.
9. **Suggest:** the LLM proposes 2–3 follow-up questions from the schema + aggregates.
10. **Persist:** the `Run` audit record (question, plan, generated SQL, result summary, prompt/completion tokens, estimated USD, timestamps) and the conversation `Message`s are written to SQLite.
11. **Output:** the API returns the rich-answer envelope; the UI renders it and the expandable code/steps/profile panel + per-query cost.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| **Gemini API** (`gemini-2.5-flash` via `google-genai`) | Narration only — turns schema + aggregates into language/chart/insight; drafts the plan + SQL. | On error/timeout/rate-limit: retry with backoff, then the node sets `state["error"]` → `handle_error` → the API returns a surfaced error (no offline stub). |
| **DuckDB** (in-process, local) | The actual query engine over the user's data files. Runs all SQL locally; raw rows never leave. | Bad SQL or query error → captured in `state["error"]`, surfaced with the attempted SQL so the user sees what was tried. |
| **SQLite** (local file via SQLAlchemy 2.0 + Alembic) | App state: dataset library, conversation history, Run audit trail. | Connection/migration error → startup fails fast; per-request error returns `api_error`. |

## Stack

> This project's concrete technology choices. The generic, every-project rules (model-naming, DB driver, dev port, real-key test rule) live in `harness/patterns/tech-stack.md`; this section is what **this** project picked. These are fixed by the existing skeleton on this branch — extend in place, never fork or rename.

- **Language:** Python 3.12 (skeleton requires `>=3.11`).
- **Agent framework:** LangGraph (`StateGraph` compiled to `agentic_ai` in `src/graph/agent.py`).
- **LLM provider + model:** Gemini / **`gemini-2.5-flash`** (low cost tier). Set via `AGENT_LLM_MODEL` / settings default. The Anthropic key is empty — do NOT use Anthropic.
- **Backend:** FastAPI (boots `api:app` on port 8001 via `uv run python -m src`).
- **Database + ORM:** **SQLite** for app state (dataset library, conversation history, audit) via **SQLAlchemy 2.0** + **Alembic**; **DuckDB** as the local query engine over the user's data files (a separate, file-data store — not the app-state DB).
- **Frontend:** Next.js 15 (static export, `output: 'export'`, `basePath: '/app'`) + React 19 + Tailwind v4. Built with `cd frontend && pnpm build` to `frontend/out/`, served by FastAPI at `/app/`.
- **Dependency management:** uv + `pyproject.toml` (Python); pnpm (frontend).

> **Assumed:** package layout follows the existing skeleton exactly — `src/` is on `pythonpath`, so imports are bare (`from db.session import ...`, `from graph.state import AgentState`, `from api import health`). There is NO `src/agent/` package; the graph lives at `src/graph/`. Do not invent new top-level package roots.

> **Assumed:** the Gemini provider default model is changed from `gemini-2.5-pro` to `gemini-2.5-flash` (`src/llm/providers/gemini.py` `DEFAULT_MODEL`), and `AGENT_LLM_MODEL=gemini-2.5-flash` is the settings default, so the chosen flash-tier model is used everywhere even if `.env` leaves the model blank.

> **Assumed:** chart rendering uses Recharts (React-native SVG charts, no canvas, plays well with static export). The backend returns a declarative `chart_spec` (type + data + axes) and the frontend renders it — the chart type is chosen by the narrate node from the aggregate shape.

> **Assumed:** Excel ingestion uses pandas + openpyxl to read each sheet, then registers each sheet as a DuckDB table; CSV is read by DuckDB directly (`read_csv_auto`) for speed on large files.

| Key library | Version | Purpose |
|-------------|---------|---------|
| fastapi | >=0.115 | REST backend (already present) |
| uvicorn[standard] | >=0.30 | ASGI server (already present) |
| pydantic / pydantic-settings | >=2.7 / >=2.3 | Request/response models + settings (already present) |
| sqlalchemy | >=2.0 | App-state ORM (already present) |
| alembic | >=1.13 | App-state migrations (already present) |
| langgraph | >=0.1 | Agent graph (already present) |
| google-genai | >=2.9.0 | Gemini client (already present) |
| structlog | >=24.1 | Structured logging (already present) |
| **duckdb** | >=1.1 | **Local query engine over user data files (ADD)** |
| **pandas** | >=2.2 | **Read Excel sheets into DuckDB; small result reshaping (ADD)** |
| **openpyxl** | >=3.1 | **Excel `.xlsx` parsing backend for pandas (ADD)** |
| recharts (frontend) | ^2.x | Declarative React charts for the rich answer (ADD to `frontend/package.json`) |

**Avoid:** Anything that sends raw data rows to the LLM (the privacy boundary). No Anthropic provider (key empty). No `gemini-2.5-pro` (cost tier is LOW → flash). No `pandas`/Python-side full-table loads for querying 100 MB files — DuckDB queries from disk; pandas is only for Excel parsing and small result reshaping. Do not create a `src/agent/` package or rename `src/graph/`.

## Deployment Model

A local long-running service on the user's own machine. Start with `uv run alembic upgrade head` (apply migrations) then `cd frontend && pnpm build` (build the static UI) then `uv run python -m src` (boots FastAPI on port 8001, serving the UI at `http://localhost:8001/app/` when `frontend/out/` exists). No cloud deployment, no containers required, no external services beyond the Gemini API.
