# Architecture — DataChat

---

## System Overview

DataChat is a single-process local web application. A FastAPI server hosts both the JSON/SSE API and the statically-exported Next.js UI under one origin (`http://localhost:8001`, UI at `/app/`). The one user interacts entirely through the browser. Uploaded spreadsheet files are stored on local disk; their metadata, profiles, conversations, and full run history live in a local SQLite database. The analysis brain is a LangGraph graph that, per question, **plans → writes pandas code → executes that code locally over the file → inspects the result → iterates** until it produces a prose answer. The LLM (Gemini) is consulted only to plan, write code, reflect, and phrase the answer — it is **never** sent raw data rows. This is the privacy spine and it is enforced in code (the only data crossing to Gemini is the question, the schema/profile, and computed result summaries) and asserted in tests.

## Component Map

```
Browser (Next.js static export, served at /app/)
    │  JSON over HTTP  +  SSE (streaming, P4)
    ▼
FastAPI app (single origin, :8001)
    ├── /datasets, /conversations, /runs, /usage    (API layer, src/api/)
    ├── StaticFiles mount  → frontend/out  (the built UI)
    ▼
Analysis runner (src/graph/runner.py)
    ▼
LangGraph graph (src/graph/)   ── plan → generate_code → execute_local → inspect → finalize
    │                                                │
    │  question + schema/profile + result summaries  │  pandas code string
    ▼                                                ▼
Gemini provider (src/llm/)                  Local sandboxed executor (src/analysis/executor.py)
 (NEVER receives raw rows)                   runs pandas over the dataframe(s) — raw rows stay local
    ▼                                                ▼
                         SQLite (src/db/) + local upload dir (data/uploads/)
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| **UI** | Next.js static export: upload, dataset/profile panel, chat transcript, collapsible code panel, step timeline, token/cost, charts/tables (`frontend/`). |
| **API** | FastAPI routers: upload+profile, ask/answer, library, conversations, runs, usage, SSE stream (`src/api/`). Thin — validates, delegates to the runner/services, shapes responses. |
| **Orchestration** | LangGraph graph + runner: the plan→code→execute→inspect→finalize loop, state, conditional edges, error handling (`src/graph/`). |
| **Analysis** | Local services the graph calls: profiler, sandboxed executor, cost/token accounting, conversation threading, viz spec, multi-file loading (`src/analysis/`). |
| **LLM** | Provider abstraction; Gemini is the configured provider (`src/llm/`). Only ever receives question + schema/profile + result summaries. |
| **Storage** | SQLite via SQLAlchemy 2.0 + Alembic migrations; uploaded files on local disk (`src/db/`, `data/`). |

## Data Flow (the privacy-preserving answer path)

1. **Upload:** browser POSTs a CSV/Excel file to `POST /datasets`. The server saves it to `data/uploads/<dataset_id>/` and the **profiler** reads it locally with pandas to produce columns, dtypes, ranges, row count (and, from P3, data-quality flags). The profile — never the rows — is persisted and returned.
2. **Ask:** browser POSTs the question to `POST /datasets/{id}/ask` (or, from P2, within a conversation). The runner creates an `analysis_run` row and invokes the graph.
3. **Plan (Gemini):** Gemini receives **only** the question + the dataset profile + (from P2) prior-turn summaries, and returns a short plan. No rows.
4. **Generate code (Gemini):** Gemini receives the plan + profile and returns a **pandas code string** referencing the in-scope dataframe `df`. No rows.
5. **Execute locally (no LLM):** the sandboxed executor runs that code over the real dataframe **on the local machine**. The raw rows never leave the process. It captures a compact **result summary** (scalars, small tables, shapes) — bounded in size.
6. **Inspect / iterate (Gemini, P3+):** Gemini sees the question + plan + code + result-summary/error (never rows) and decides: answer is good → finalize; code errored or result is wrong/empty → revise code and loop, up to a hard step cap.
7. **Finalize (Gemini):** Gemini phrases the prose answer from the question + computed result summary (+ from P3 assumptions/uncertainty, follow-up suggestions). Tokens and cost are accounted; the run (question, code, result, tokens, cost, timestamps, steps) is persisted.
8. **Output:** the API returns the prose answer, the code that ran, token/cost, (P3) timeline steps + follow-ups, (P4) chart/table spec — streamed token-by-token over SSE in P4.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| **Gemini API** | Plan, generate code, inspect/reflect, phrase answer. Receives only question + profile + result summaries. | On timeout/rate-limit/error: bounded retry with backoff in the provider; if still failing, the run finalizes with status `failed` and a surfaced error — never a fabricated answer. Tests call the real API via `.env`. |
| **Local filesystem** | Store uploaded files (`data/uploads/`) and the SQLite DB (`data/agent.db`). | Disk/permission error surfaces as an upload/run error; no partial-state corruption (run row marked failed). |

There are **no other external services** — DataChat is standalone by design.

## Stack

> Concrete choices for this project. Generic rules (model-naming, DB driver, dev port, real-key tests) live in `harness/patterns/tech-stack.md`.

- **Language:** Python 3.12 (backend), TypeScript (frontend).
- **Agent framework:** LangGraph (multi-node graph with a conditional iterate loop — see [agent.md](agent.md)).
- **LLM provider + model:** **Gemini is THE provider for this build.** Key env var `AGENT_GEMINI_API_KEY` (already set in `.env`); provider auto-detected by `src/llm/client.py`. Default model **`gemini-2.5-flash`** (set `AGENT_LLM_MODEL=gemini-2.5-flash`). Rationale: this graph makes 3–5 Gemini calls per question (plan, code, inspect×N, finalize); Flash's lower latency and ~10× lower cost vs `gemini-2.5-pro` are the right trade for the sub-30s + per-question-cost + (P4) streaming goals, and code-generation over a known schema does not need Pro-level reasoning. **Anthropic remains only an optional fallback** (the skeleton still supports it via `AGENT_ANTHROPIC_API_KEY`); it is not used in this build. The model id is env-configurable, so a node can be escalated to `gemini-2.5-pro` later without a code change.
- **Backend:** FastAPI (JSON + SSE), Uvicorn on port **8001**, single origin.
- **Database + ORM:** **SQLite is the production database** for this single-user local tool (no PostgreSQL anywhere — tests run against SQLite too). SQLAlchemy 2.0 ORM, Alembic migrations.
- **Frontend:** Next.js 15 + React 19, **static export** (`output: 'export'`, `basePath: '/app'`), Tailwind. Built to `frontend/out/` and mounted by FastAPI at `/app/` — single origin, no CORS, no separate dev server in production. Extends the existing `frontend/` skeleton in place.
- **Dependency management:** uv + `pyproject.toml` (Python); pnpm (frontend).

| Key library | Version | Purpose |
|-------------|---------|---------|
| fastapi | >=0.115 | HTTP + SSE API |
| uvicorn[standard] | >=0.30 | ASGI server (:8001) |
| langgraph | >=0.1 | Agent graph orchestration |
| google-genai | >=2.9 | Gemini provider |
| pandas | (env-present) | Local data analysis; the executor runs generated pandas |
| openpyxl | add in P1 | Read `.xlsx` Excel files via pandas |
| sqlalchemy | >=2.0 | ORM |
| alembic | >=1.13 | Migrations |
| pydantic / pydantic-settings | >=2.7 / >=2.3 | Domain models + settings |
| structlog | >=24.1 | Structured logging / observability |
| (frontend) recharts or vega-lite | P4 | Interactive charts |

**Avoid:** PostgreSQL / psycopg (SQLite is the production DB here); any path that sends raw data rows to the LLM (violates the privacy spine); `eval`/unrestricted `exec` of generated code outside the sandboxed executor; arbitrary network/filesystem access from generated code; a hardcoded operation-list interpreter instead of generated pandas (anti-pattern #22).

## Single-Origin `/app/` Serving

The Next.js app is configured with `output: 'export'`, `basePath: '/app'`, `trailingSlash: true` (already in `frontend/next.config.ts`). `cd frontend && pnpm build` emits a static site to `frontend/out/`. `src/api/__init__.py` mounts that directory at `/app` via `StaticFiles(..., html=True)` when it exists (API-only mode if it doesn't). The browser therefore loads the UI and calls the API from the **same origin** (`localhost:8001`) — no CORS, no proxy. The styled-render gate requires the built CSS bundle to contain real Tailwind utility selectors (no unexpanded `@tailwind`).

## Deployment Model

A single long-running local process started with `uv run python -m src` (Uvicorn, `:8001`), after `uv run alembic upgrade head` and `cd frontend && pnpm build`. Single user, local machine, no auth, no cloud. Data lives under `data/` (SQLite DB + uploaded files).
