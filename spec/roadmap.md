# Roadmap

---

## What This Agent Does

The Data Analyst Agent is a chat application where a user uploads tabular datasets (CSV now, Excel later) and asks questions about them in natural language. The agent translates each question into analytical SQL, runs it against a fast columnar engine, and returns a formatted natural-language answer plus a result table. It behaves like a senior data analyst: it understands the dataset's schema, writes correct SQL, and explains results — while keeping LLM token usage minimal by sending only schema (column names and types), never raw rows, to the model.

## Who Uses It

Analysts, operators, and non-technical decision-makers who have data in spreadsheets and want answers without writing SQL or opening a BI tool. Their goal: ask "what's the average order value by region?" and get a trustworthy answer and table back in seconds.

## Core Problem Being Solved

Getting answers from a CSV today means either writing SQL/pandas by hand or wrestling a heavyweight BI tool. This agent replaces that with a chat box: upload, ask, get a verified answer with the exact query logged for auditing.

## Success Criteria

- [ ] A user can upload a CSV and see it registered as a queryable dataset.
- [ ] A natural-language question returns a correct formatted text answer plus a result table, end-to-end against real Gemini.
- [ ] Every executed SQL statement is written to the audit log with its dataset, status, and row count.
- [ ] Each LLM round-trip for a query sends schema only (column names/types), never row data.
- [ ] Sessions and their messages persist across page reloads.

## What This Agent Does NOT Do (Out of Scope)

- Does NOT write back to or mutate uploaded data (read-only analytics).
- Does NOT connect to external/live databases or warehouses (upload-only).
- Does NOT do unbounded data science (ML training, forecasting, statistical modelling beyond SQL aggregation).
- Does NOT support real-time/streaming data.
- Does NOT support user accounts/auth in v1 (single-tenant, session-scoped).
- Does NOT render charts/dashboards or surface an audit UI in Phase 1 (later phases; stubbed in the UI).

## Key Constraints

- **Token economy is a first-class goal.** Schema-only context, compact prompts, one LLM call per query on the happy path. See [architecture.md](architecture.md#token-economy).
- LLM is Gemini (`gemini-2.5-flash` default) via `AGENT_GEMINI_API_KEY`; provider/model env-configurable.
- Analytical engine is DuckDB; metadata/sessions/audit live in the relational DB at `AGENT_DATABASE_URL` (SQLite).
- Dev port **8001**. Tests/gates run against the REAL Gemini API using `.env`.

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** Backend is minimal but REAL on the one core path. Frontend is visually complete: real UI for upload+query+table PLUS clearly-labelled NON-FUNCTIONAL stubs for charts/dashboards/audit/multi-dataset.

### Phase 1 — Upload CSV → ask → answer + table

- **Goal:** A user uploads one CSV, types one natural-language question, and gets back a real formatted text answer and a result table, end-to-end against real Gemini. Every SQL execution is written to the audit log.
- **Independent slices (parallel build units):**
  - `slice-backend` (backend) — CSV upload → DuckDB load; one-call query pipeline (schema → Gemini → SQL → DuckDB execute → format); audit-log write; datasets/sessions/messages persistence; REST endpoints. Deps: none.
  - `slice-frontend` (frontend) — chat screen with file upload, message list, result-table rendering; labelled non-functional stubs for charts/dashboards/audit/multi-dataset. Deps: none (codes against the [api.md](api.md) contract; both slices implement the same contract independently).
- **Key surfaces / files:**
  - backend: `src/api/datasets.py`, `src/api/sessions.py` (new); replace `src/graph/nodes.py`, `src/graph/state.py`, `src/graph/agent.py`, `src/graph/edges.py`, `src/graph/runner.py`; `src/prompts/sql_generate.md`, `src/prompts/format_answer.md` (replacing `transform.md`); `src/analytics/duckdb_store.py`, `src/analytics/ingest.py` (new); `src/db/models.py` (add Dataset, Session, Message, AuditLog); `alembic/versions/0002_*.py`; `tests/`.
  - frontend: `frontend/src/app/page.tsx`, `frontend/src/app/components/*` (new chat/upload/table/stub components).
- **Gate command:** `uv run alembic upgrade head && uv run pytest`
- **How the user tests it (handoff seed):** Run `uv run alembic upgrade head`, start backend `uv run uvicorn api.app:app --port 8001` (or the repo's run script), start frontend `pnpm --dir frontend dev`. Open the chat UI, click "Upload CSV", pick a CSV (e.g. an orders file). After it registers, type "What is the total revenue by region?" and send. Expect a formatted text answer and a result table below it. The sidebar shows the uploaded dataset. Buttons/panels labelled "Charts (coming soon)", "Dashboards (coming soon)", "Audit log (coming soon)", and "Add another dataset (coming soon)" are visible but disabled — these are intentional stubs, not bugs.

### Phase 2 — Charts from query results

- **Goal:** A query result can be rendered as a chart (bar/line/pie) when the shape suits it; the agent suggests a chart type.
- **Independent slices:**
  - `slice-backend` (backend) — extend the format node to emit an optional chart spec (type + x/y mappings) alongside the table. Deps: none.
  - `slice-frontend` (frontend) — wire the "Charts" stub into a real chart renderer. Deps: none (consumes the chart-spec contract).
- **Key surfaces / files:** backend `src/graph/nodes.py`, `src/prompts/format_answer.md`, `src/domain/`; frontend `frontend/src/app/components/Chart*.tsx`.
- **Gate command:** `uv run pytest tests/test_chart_spec.py`
- **How the user tests it:** Ask a question that aggregates by category; expect a chart to render above/below the table.

### Phase 3 — Multi-dataset cross-query

- **Goal:** Upload multiple datasets; ask questions that JOIN across them.
- **Independent slices:** backend — register N datasets in one DuckDB connection, include all schemas in context, support JOINs; frontend — wire the "Add another dataset" stub, dataset selector. Deps: frontend depends on backend's multi-dataset list endpoint (declared dependency).
- **Key surfaces / files:** backend `src/analytics/duckdb_store.py`, `src/graph/nodes.py`, `src/api/datasets.py`; frontend dataset-sidebar components.
- **Gate command:** `uv run pytest tests/test_cross_dataset.py`
- **How the user tests it:** Upload two related CSVs; ask a question spanning both; expect a joined answer.

### Phase 4 — Senior-analyst multi-step reasoning

- **Goal:** Hard questions trigger a plan→execute→refine loop (multiple SQL steps, self-correction on SQL errors) instead of a single call.
- **Independent slices:** backend only — add planner/critic nodes and a bounded retry loop to the graph. Deps: none.
- **Key surfaces / files:** backend `src/graph/agent.py`, `src/graph/nodes.py`, `src/graph/edges.py`, `src/prompts/plan.md`, `src/prompts/critic.md`.
- **Gate command:** `uv run pytest tests/test_multistep.py`
- **How the user tests it:** Ask a multi-part question; expect a correct answer where a single SQL pass would have failed.

### Phase 5 — Audit UI + session UX + Excel

- **Goal:** Surface the audit log in the UI, polish session switching/rename, and accept `.xlsx` uploads.
- **Independent slices:** backend — audit-log read endpoint, Excel ingest (`openpyxl`); frontend — wire "Audit log" stub into a real panel, session list UX. Deps: frontend audit panel depends on backend audit endpoint (declared).
- **Key surfaces / files:** backend `src/api/audit.py`, `src/analytics/ingest.py`; frontend audit + session components.
- **Gate command:** `uv run pytest tests/test_audit_api.py tests/test_excel_ingest.py`
- **How the user tests it:** Open the Audit panel and see logged SQL operations; upload an `.xlsx` and query it; switch sessions.
