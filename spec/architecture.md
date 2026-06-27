# Architecture

DataChat — a local, single-origin data-analysis agent whose defining architectural property is a hard privacy boundary: raw data rows never leave the machine; only schema + computed aggregates reach the LLM.

---

## System Overview

DataChat runs entirely on the user's machine as a single-origin app: a FastAPI backend serves a Next.js static export at `http://localhost:8001/app/` and exposes a small JSON API on the same origin. The user uploads a CSV (Phase 1) or connects a PostgreSQL database (Phase 2). When the user asks a plain-English question, a LangGraph agent (a) profiles the data's **schema** locally, (b) asks Gemini 2.5 Flash to plan an aggregation over that schema, (c) **executes that aggregation locally** with DuckDB/pandas over the full dataset, and (d) asks Gemini to phrase the resulting **aggregate** as a plain-English answer plus a chart spec. The only things ever sent to Gemini are the schema and small computed aggregates — never raw rows. The app keeps its own metadata (datasets, questions, conversation turns) in a local SQLite store; the analysed data lives in a local DuckDB working store and is never transmitted.

## Component Map

```
        Browser (Next.js static export @ /app/)
                      │  same-origin JSON (upload, ask)
                      ▼
              FastAPI (src/api/)
        ┌───────────┼─────────────────┐
        ▼           ▼                 ▼
   datasets.py    ask.py          health.py
        │           │
        │           ▼
        │     graph/runner.py ──► LangGraph agent (graph/agent.py)
        │           │
        │   ┌───────┴─────────────────────────────────┐
        │   ▼                ▼              ▼           ▼
        │ profile_data   plan_compute   execute_local  phrase_answer
        │ (LOCAL)        (LLM: schema)  (LOCAL, full)  (LLM: aggregates)
        │   │                                  │
        ▼   ▼                                  ▼
   DuckDB working store (LOCAL rows)    LLMClient → Gemini 2.5 Flash
        │                                      ▲
        ▼                          ════════════╪════════════════════
   SQLite app store (metadata)     PRIVACY BOUNDARY: only schema +
   (src/db/, alembic/)             aggregates cross this line
```

The double line marks the **privacy boundary**: everything left of it (DuckDB working store, raw rows, full-table computation) stays local; only the schema summary and computed aggregates produced by the boundary surface cross to the LLM.

## Layers

| Layer | Responsibility |
|-------|----------------|
| Frontend (Next.js static export) | Upload UI, chat box, answer panel, chart render, labelled stubs. Same-origin fetch only. |
| API (FastAPI `src/api/`) | Upload/ask/health endpoints; `ok()`/`api_error()` envelopes; invokes the runner. |
| Agent (LangGraph `src/graph/`) | Orchestrates profile → plan → execute-local → phrase across nodes; holds run state. |
| Local compute (`src/tools/`) | DuckDB/pandas ingestion, schema profiling, aggregate computation — **the privacy boundary lives here.** |
| LLM (`src/llm/`) | `LLMClient` → Gemini 2.5 Flash; the ONLY egress to the model; receives schema + aggregates only. |
| App store (SQLite + SQLAlchemy, `src/db/`) | Metadata: datasets, questions, conversation turns. Not the analysed data. |
| Working store (DuckDB, local file/in-memory) | Holds the uploaded/connected rows for local computation. Never transmitted. |

## Data Flow

1. **Trigger:** user uploads a CSV (`POST /datasets`) → it is loaded into the local DuckDB working store; a `Dataset` metadata row is written to SQLite; the schema (columns + types + row count) is profiled locally and returned.
2. The user asks a question (`POST /ask` with `dataset_id` + `question`). FastAPI calls `run_agent(...)`.
3. **`profile_data` (LOCAL):** reads the schema summary for the dataset (column names, types, row count, a few example *aggregate* facts like min/max/distinct-count). No raw rows.
4. **`plan_compute` (LLM — schema only):** sends the **schema summary + the question** to Gemini 2.5 Flash; receives a structured compute plan (which columns to group by, which to aggregate, which function). **No data rows are in this prompt.**
5. **`execute_local` (LOCAL, full data):** validates the plan against the schema, then runs the aggregation over the **full dataset** in DuckDB. Produces a small result table (aggregates) — this is the only data artifact that may cross the boundary.
6. **`phrase_answer` (LLM — aggregates only):** sends the **question + the small aggregate result** to Gemini; receives a plain-English answer + a chart spec (type + the aggregate series). **No raw rows** — only the already-aggregated result.
7. **`finalize`:** persists a `Question` row (answer text, chart spec) to SQLite and returns `{answer, chart}` to the browser.
8. **Output:** the browser shows the plain-English answer and renders the chart.

## Privacy Boundary (First-Class Constraint)

**Rule:** Only two kinds of payload may ever be passed to `LLMClient.call_model`: (1) a **schema summary** (column names, types, row count, and column-level *aggregate* descriptors such as min/max/distinct-count/null-count), and (2) a **computed aggregate result** (a small grouped/summarized table). Raw rows, individual records, full columns, or row samples must NEVER be passed to the LLM.

**Where it is enforced (the exact code surface):**
- `src/tools/profile.py` — `build_schema_summary(...)` is the ONLY function that produces the schema payload; it returns column metadata + scalar aggregates, never rows.
- `src/tools/compute.py` — `run_aggregation(...)` executes the plan locally and returns a bounded aggregate result; `assert_no_raw_rows(payload)` is a guard that rejects any payload exceeding the aggregate-size/shape contract before it can reach the LLM.
- In the graph (`src/graph/nodes.py`), the `plan_compute` and `phrase_answer` nodes call `assert_no_raw_rows(...)` on their outgoing LLM payload immediately before `LLMClient().call_model(...)`. No other node calls the LLM. This is the single chokepoint.

This boundary is proven by `tests/phase1/test_privacy_boundary.py`, which spies on the payload handed to the LLM and asserts it contains only schema/aggregate fields and no raw cell values from a sentinel-laden fixture. See [agent.md → Privacy Boundary Enforcement](agent.md#privacy-boundary-enforcement).

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Gemini 2.5 Flash (via `AGENT_GEMINI_API_KEY`) | Plan the aggregation; phrase the answer + choose chart | Network/rate-limit error → surfaced as `api_error("LLM_UNAVAILABLE", ...)`; Phase 4 adds retry/backoff + degraded message |
| DuckDB (local) | Local SQL over CSV (Phase 1) and Postgres scan (Phase 2); full-data aggregation | Bad file/query → `api_error("COMPUTE_FAILED", ...)`; never crashes the server |
| PostgreSQL (user-supplied, Phase 2) | The analysed data source (read-only) | Unreachable/invalid string → `api_error("SOURCE_UNREACHABLE", ...)` at connect time |
| SQLite (local app store) | Metadata: datasets, questions, conversation | File error → startup fails fast (init_db) |

## Stack

> This project's concrete choices. Generic rules (model-naming, DB driver, dev port, real-key tests) live in `harness/patterns/tech-stack.md`.

- **Language:** Python 3.12 (backend); TypeScript/React (frontend).
- **Agent framework:** LangGraph (StateGraph, compiled once at import as `agentic_ai`).
- **LLM provider + model:** Gemini 2.5 Flash — model id `gemini-2.5-flash`. Auto-detected from `AGENT_GEMINI_API_KEY`; `GeminiProvider.DEFAULT_MODEL` must be set to `gemini-2.5-flash` for this project (the skeleton default is `gemini-2.5-pro` — change it).
- **Backend:** FastAPI (single-origin; serves the static frontend at `/app`).
- **Database + ORM:** SQLite + SQLAlchemy 2.0 (declarative `Mapped` types) for the app's OWN metadata store. Alembic for migrations. SQLite is correct here — this is a personal local tool and the app store is not the analysed data.
- **Local compute engine:** DuckDB (primary — fast local SQL over CSV/Parquet and, Phase 2, over a Postgres scan), with pandas for convenience profiling. This is what keeps rows local.
- **Frontend:** Next.js 15 static export (React 19) served from `frontend/out` at `/app`; **Recharts** for charts (lightweight, declarative, React-native, no canvas plumbing).
- **Dependency management:** uv + `pyproject.toml` (Python); pnpm (frontend).

| Key library | Version | Purpose |
|-------------|---------|---------|
| langgraph | >=0.2 | Agent graph orchestration |
| fastapi | >=0.115 | Backend API + static mount |
| uvicorn | >=0.30 | ASGI server (`localhost:8001`) |
| sqlalchemy | >=2.0 | ORM for the app metadata store |
| alembic | >=1.13 | Migrations for the app store |
| pydantic / pydantic-settings | >=2.7 / >=2.5 | Domain models + settings |
| google-genai | >=0.3 | Gemini 2.5 Flash client (existing provider) |
| duckdb | >=1.1 | Local full-data SQL compute (boundary stays local) |
| pandas | >=2.2 | CSV ingestion + convenience profiling |
| duckdb `postgres_scanner` | (extension) | Phase 2: scan PostgreSQL locally |
| next / react | 15 / 19 | Frontend static export |
| recharts | >=2.12 | Chart rendering |

**Avoid:**
- Sending raw rows, full columns, or row samples to the LLM — violates the core constraint. The ONLY egress is schema + aggregates via the boundary surface.
- PostgreSQL/MySQL/Node for the app's OWN store — SQLite is the deliberate choice for a personal local tool.
- A second Python package (`src/agent/` or similar) — extend `src/` in place; one package, bare imports.
- Heavy chart stacks (D3 from scratch, canvas libs) — Recharts is sufficient and light.
- Cloud/remote deployment, auth frameworks, background schedulers — out of scope.

## Deployment Model

Local single-origin app. The user runs `python agent.py --run`, which applies Alembic migrations, builds the Next.js static export, and serves the API at `http://localhost:8001` with the UI at `http://localhost:8001/app/`. No containers, no cloud, no auth — one user on one machine. Secrets (`AGENT_GEMINI_API_KEY`) come from `.env`.
