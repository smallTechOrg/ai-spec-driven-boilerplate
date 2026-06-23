# Roadmap

---

## What This Agent Does

A token-economical data analyst agent that lets a user upload their own tabular data (CSV/Excel) and ask questions about it in plain English. It behaves like a senior data analyst: it inspects the dataset's schema, writes the SQL needed to answer the question, runs that SQL locally against a fast embedded analytics engine, and replies with a concise narrative interpretation plus a formatted result table. Every data operation is recorded in a persistent audit trail, and sessions persist across restarts so a user's datasets and history are always there when they return.

## Who Uses It

A single analyst, operator, or domain expert working on their own machine who has data in spreadsheets and wants answers without writing SQL. They value (a) keeping their raw data on their own machine, (b) trustworthy answers they can audit, and (c) low LLM cost.

## Core Problem Being Solved

Answering ad-hoc questions over a spreadsheet today means either writing SQL/pandas by hand or pasting data into a chatbot — the former is slow and skill-gated, the latter leaks the entire dataset to a third party and is expensive in tokens. This agent gives natural-language analysis while keeping the raw rows local and sending the LLM only schema and tiny samples/aggregates.

## Success Criteria

- [ ] A user can upload a CSV or Excel file and see it appear as an organised dataset with its inferred column schema and row count.
- [ ] A user can ask one natural-language question over a dataset and receive a senior-analyst narrative plus a correctly-populated result table derived from real SQL run on their data.
- [ ] No question ever sends more than a hard-capped number of sample rows (default 5) to the LLM — verified by an automated test that inspects the outgoing prompt.
- [ ] Every question produces an audit-log entry (timestamp, NL question, generated SQL, row count, duration) that is viewable in the UI and persists across a server restart.
- [ ] Dataset rows never leave the machine except as schema + capped samples/aggregates inside an LLM prompt — verified by test.

## What This Agent Does NOT Do (Out of Scope)

- Does NOT send full dataset rows, full columns, or arbitrary row dumps to the LLM (only schema + capped samples/aggregates).
- Does NOT (in v1) render charts, dashboards, or visualizations — those surfaces are present as clearly-labelled non-functional stubs.
- Does NOT (in v1) answer questions that join across multiple datasets in one NL query.
- Does NOT connect to external/cloud databases or warehouses — data source is local file upload only.
- Does NOT support multi-user accounts, authentication, or remote multi-tenancy — it is a local single-user tool.
- Does NOT write back to or mutate the user's source files.
- Does NOT execute arbitrary user-supplied SQL — only SQL the agent generates from an NL question (read-only).

## Key Constraints

1. **Token economy is critical (testable).** The LLM is never sent raw rows beyond a hard cap (default 5 sample rows per column-set, configurable via `AGENT_MAX_SAMPLE_ROWS`). Prompts carry schema, types, and small aggregates only. This is enforced by code and asserted by tests.
2. **Full audit trail (testable).** Every SQL/data operation is persisted with timestamp, NL question, generated SQL, row count, and duration, and is viewable + exportable in the UI.
3. **Local-only.** All data ingestion, storage, and query execution happen on the local machine via an embedded engine; the only network egress is the LLM API call, which carries metadata only.
4. **Latency.** A typical single-dataset question should return in a handful of seconds (one LLM round-trip for SQL generation + one for narration, plus local query time).

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** Its backend is minimal but REAL on the one core path (no fake data on the tested path). Its frontend is visually complete: real UI for the working path PLUS clearly-labelled NON-FUNCTIONAL stubs for charts/dashboards/cross-dataset query, so the user sees the vision. Later phases wire those stubs into real functionality, one increment at a time.

### Phase 1 — Upload → Ask → SQL → Narrative + Table + Audit

- **Goal:** A user opens the app, uploads a CSV/Excel file (auto-creating a persistent session and an organised dataset in DuckDB), types one natural-language question, and gets back a senior-analyst narrative plus a formatted result table produced by real LLM-generated SQL run locally on DuckDB. Every operation lands in a persistent, viewable audit log. Charts/dashboards/cross-dataset query are visible but labelled stubs.

- **Independent slices (parallel build units):** Each slice owns disjoint files. Slices A and B both read the contracts in `spec/data.md` and `spec/api.md`, so they can be built concurrently without waiting on each other's code; slice C builds against the `spec/api.md` contract and uses labelled stubs until the API is live.
  - `data-layer` (backend) — SQLAlchemy models (Session, Dataset, AuditLog), Alembic migration `0002`, DuckDB ingestion service (CSV/Excel → DuckDB table + schema profile), and the audit-logging helper. Deps: none.
  - `agent-api` (backend) — LangGraph data-analyst nodes (profile_schema → generate_sql → execute_sql → narrate), token-economy guard, the runner, and the FastAPI endpoints (upload/list/ask/audit/health). Consumes the model + service contracts from `spec/data.md`/`spec/api.md` (not the other slice's code). Deps: none at build time; the gate runs after both A and B land.
  - `frontend` (frontend) — upload panel, dataset list, ask-a-question box, narrative + result-table renderer, audit-log viewer + export button, and clearly-labelled non-functional stub cards for Charts, Dashboards, and Cross-Dataset Query. Builds to `spec/api.md` contract. Deps: none.

- **Key surfaces / files:**
  - `data-layer`: `src/db/models.py` (add `SessionRow`, `DatasetRow`, `AuditLogRow`), `alembic/versions/0002_*.py`, `src/services/ingest.py`, `src/services/duckdb_store.py`, `src/services/audit.py`, `src/config/settings.py` (add `duckdb_path`, `max_sample_rows`).
  - `agent-api`: `src/graph/state.py`, `src/graph/nodes.py` (replace `transform_text`), `src/graph/edges.py`, `src/graph/agent.py`, `src/graph/runner.py`, `src/prompts/generate_sql.md`, `src/prompts/narrate.md`, `src/api/datasets.py`, `src/api/ask.py`, `src/api/audit.py`, `src/api/__init__.py` (register routers), `src/domain/analysis.py`.
  - `frontend`: `frontend/src/app/page.tsx`, `frontend/src/app/components/*` (UploadPanel, DatasetList, AskBox, ResultView, AuditLog, StubCard).
  - Tests: `tests/unit/test_ingest.py`, `tests/unit/test_token_economy.py`, `tests/unit/test_audit.py`, `tests/integration/test_ask_flow.py` (real Gemini).

- **Gate command:**
  ```
  uv run alembic upgrade head && uv run pytest tests -q && (cd frontend && pnpm build)
  ```
  Runs the real Alembic migration on the configured DB, the full test suite (the `test_ask_flow` integration test hits the real Gemini API using `AGENT_GEMINI_API_KEY` from `.env`; the token-economy and ingest tests use real DuckDB), and proves the static frontend builds.

- **How the user tests it (handoff seed):**
  1. `uv run alembic upgrade head` then `(cd frontend && pnpm build)` then `uv run python -m src` (server on `http://localhost:8001`).
  2. Open **http://localhost:8001/app/**.
  3. In the **Upload** panel, choose a CSV or Excel file (e.g. a sales export) and click Upload. Expect it to appear in the **Datasets** list with its name, row count, and column schema.
  4. In the **Ask a question** box, select the dataset and type e.g. *"What were total sales by region?"* and submit. Expect a short analyst narrative ("Region X led with …") above a formatted result table with the actual numbers.
  5. Open the **Audit Log** panel: expect a new row showing timestamp, your question, the generated SQL, the row count, and duration in ms. Click **Export** to download it. Restart the server and confirm the dataset and audit entry are still there.
  6. **Labelled stubs (NOT bugs):** the **Charts**, **Dashboards**, and **Cross-Dataset Query** cards show a "Coming soon" badge and are intentionally non-interactive.

### Phase 2 — Charts & visual responses

- **Goal:** When a result table is suitable for visualization, the agent proposes a chart spec and the UI renders it — turning the Phase-1 Charts stub into a real feature.
- **Independent slices (parallel build units):**
  - `chart-agent` (backend) — add a `propose_chart` node + prompt that, given the result schema (not raw rows beyond the cap), emits a small typed chart spec (type, x, y, series); extend `AskResponse` with an optional `chart` field. Deps: none (extends Phase-1 graph in place).
  - `chart-frontend` (frontend) — replace the Charts stub card with a real chart renderer driven by the `chart` field. Deps: builds to the extended `spec/api.md` contract.
- **Key surfaces / files:** `src/graph/nodes.py`, `src/prompts/propose_chart.md`, `src/domain/analysis.py`, `src/api/ask.py`; `frontend/src/app/components/ChartView.tsx`, `frontend/src/app/components/StubCard.tsx` (remove Charts stub).
- **Gate command:** `uv run pytest tests/integration/test_chart_flow.py -q && (cd frontend && pnpm build)` (real Gemini).
- **How the user tests it (handoff seed):** Open http://localhost:8001/app/, ask a question that aggregates by a category over a measure; expect a rendered chart beneath the table. The Dashboards and Cross-Dataset cards remain labelled stubs.

### Phase 3 — Senior-analyst workflow (clarify → plan → recommend)

- **Goal:** For ambiguous or multi-step questions, the agent first clarifies (asking the user a question when confidence is low) and ends with explicit recommendations / next steps, completing the senior-analyst loop.
- **Independent slices (parallel build units):**
  - `workflow-agent` (backend) — add `clarify` (human-in-the-loop checkpoint) and `recommend` nodes + conditional routing on a confidence flag; persist pending-clarification state on the session. Deps: none.
  - `workflow-frontend` (frontend) — render clarification prompts inline in the Ask flow and a "Recommendations" section in the result. Deps: extended `spec/api.md` contract.
- **Key surfaces / files:** `src/graph/nodes.py`, `src/graph/edges.py`, `src/graph/agent.py`, `src/prompts/clarify.md`, `src/prompts/recommend.md`, `src/api/ask.py`; `frontend/src/app/components/AskBox.tsx`, `frontend/src/app/components/ResultView.tsx`.
- **Gate command:** `uv run pytest tests/integration/test_workflow_flow.py -q && (cd frontend && pnpm build)` (real Gemini).
- **How the user tests it (handoff seed):** Ask a deliberately vague question (e.g. "show me the trends") and expect a clarifying question; answer it and expect a narrative ending with concrete recommendations.

### Phase 4 — Cross-dataset NL query & dashboards

- **Goal:** Ask one question spanning multiple datasets (DuckDB joins across registered tables) and pin multiple results into a saved dashboard — turning the last two Phase-1 stubs real.
- **Independent slices (parallel build units):**
  - `multi-dataset-agent` (backend) — schema profiling across selected datasets, multi-table SQL generation (still under the sample-row cap), and a `Dashboard`/`DashboardItem` data model + endpoints. Deps: none.
  - `dashboard-frontend` (frontend) — multi-dataset selector in the Ask box and a dashboard grid that renders pinned results/charts. Deps: extended `spec/api.md`/`spec/data.md` contract.
- **Key surfaces / files:** `src/graph/nodes.py`, `src/services/duckdb_store.py`, `src/db/models.py` (add `DashboardRow`, `DashboardItemRow`), `alembic/versions/0003_*.py`, `src/api/dashboards.py`; `frontend/src/app/components/Dashboard.tsx`, `frontend/src/app/components/AskBox.tsx`.
- **Gate command:** `uv run alembic upgrade head && uv run pytest tests/integration/test_cross_dataset_flow.py -q && (cd frontend && pnpm build)` (real Gemini).
- **How the user tests it (handoff seed):** Upload a second dataset, select both, ask a question that joins them, expect a joined result; pin two results to a dashboard and confirm they persist across restart.
