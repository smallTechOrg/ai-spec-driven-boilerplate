# Architecture

## System Overview

The Lead Gen Agent is a single-process Python web app. The operator submits a filter form; a FastAPI handler starts a LangGraph pipeline (`search → extract → score → persist`) which discovers candidates via a pluggable `SearchTool`, enriches them with basic firmographics, scores each via an LLM, and persists runs + leads to Postgres. The same web app serves the runs and leads browse/export UI.

## Component Map

```
[Operator (browser)]
        ↓
[FastAPI + Jinja UI]  ──▶  [LangGraph pipeline: search → extract → score → persist]
        ↓                         │           │          │
   [Postgres (runs, leads)]       ▼           ▼          ▼
                              [SearchTool] [LLMClient]  [Repository]
                              (DuckDuckGo)  (Gemini /
                                             Stub)
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| Web (FastAPI + Jinja) | Render forms/pages, accept trigger POSTs, stream CSV, inject stub banner |
| Graph (LangGraph) | Orchestrate `search → extract → score → persist` |
| Tools | `SearchTool` (DuckDuckGo / pluggable), `LLMClient` (Gemini / Stub) |
| Domain | Pydantic models: `Filters`, `Candidate`, `Lead`, `Run` |
| DB | SQLAlchemy 2.0 + psycopg2; Alembic migrations |

## Data Flow

1. **Trigger:** operator submits the `/runs` POST with `country`, `industry`, `size_band`.
2. **Create run:** a `Run` row is inserted with `status=pending` and filter JSON.
3. **Search node:** `SearchTool.search(query)` returns candidate URLs + snippets.
4. **Extract node:** LLM extracts firmographics from each snippet → `Candidate` list.
5. **Score node:** LLM assigns 0–100 score + one-sentence rationale per candidate.
6. **Persist node:** each scored `Lead` is written to `leads` referencing the run; run marked `completed`.
7. **Output:** operator views `/leads` (ranked, filterable) and downloads `/leads.csv`.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Postgres | Persist runs + leads | App fails at startup; surfaced via /health |
| DuckDuckGo HTML | Candidate discovery (v0.1) | Empty candidate list; run completes with 0 leads |
| Gemini API | Extract + score | Falls back to stub when `GEMINI_API_KEY` is unset; banner shown |

## Deployment Model

Local dev: `uv run python -m lead_gen_agent` serves on `:8001`. Single-process uvicorn. v0.1 is not hosted; hand-off target is a one-off container later.
