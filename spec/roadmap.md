# Roadmap

## What This Agent Does

A personal data analysis agent that lets a single user upload CSV or Excel files, ask plain-English questions about the data, and instantly receive an interactive chart (bar, line, or scatter) plus a written summary of key findings — all rendered in the browser. The agent handles all data computation locally; only the column schema and up to 20 sample rows are sent to the LLM.

## Who Uses It

A single user (personal tool). They upload their own data files — sales reports, experiment results, survey exports — and want quick visual answers without writing SQL or pandas code.

## Core Problem Being Solved

Turning CSV or Excel data into visual insights requires pandas or SQL expertise. This agent eliminates that barrier: the user asks in plain English, the agent writes and executes the code locally, and the user gets a chart and a written summary with zero friction.

## Success Criteria

- [ ] Upload a CSV and ask a question → chart and summary appear within 10 seconds on the tested path
- [ ] The chart type is appropriate for the question (bar for category comparison, line for trends, scatter for correlation)
- [ ] The chart renders real computed data from the full file (not Gemini's illustrative example values)
- [ ] The privacy rule is enforced: Gemini receives only the column schema and up to 20 sample rows — never the full dataset
- [ ] The Phase 2 "Connect Database" stub is clearly visible and labelled, and never looks like a broken feature

## What This Agent Does NOT Do (Out of Scope)

- Multi-user support — personal tool only; no authentication or access control
- Data editing or transformation — read-only analysis
- Export to PDF, Excel, or image formats
- PostgreSQL database connection — deferred to Phase 2
- Multi-turn conversational memory — each question is independent in Phase 1
- Natural language answers without a chart
- Cloud deployment

## Key Constraints

- Privacy: Gemini receives only column schema + up to 20 sample rows — the full dataset stays local at all times
- Cost: Gemini 2.5 Pro; prompt size is minimized by sending only schema + sample
- Local only: no cloud deployment in Phase 1
- Single file active at a time in Phase 1
- LangGraph graph and AgentState are wired in Phase 1 — not deferred

## Phases of Development

### Phase 1 — Upload + Analysis + Chart

**Goal:** User uploads a CSV or Excel file, asks a plain-English data question, and gets back an interactive Recharts chart (bar, line, or scatter) plus a written summary — the complete primary journey, working end-to-end the first time it is tested.

**Independent slices (parallel build units):**

- `slice-a` (backend) — file upload endpoint, datasets SQLite table + Alembic migration, LangGraph analyze_data node (Gemini call + pandas execution), POST /analyze API route, integration tests. No dependency on slice-b.
- `slice-b` (frontend) — Next.js page: file dropzone, chat input, Recharts chart (bar/line/scatter), summary card, Phase 2 "Connect Database" stub button + modal. No dependency on slice-a.

**Key surfaces / files:**

slice-a owns:
- `src/graph/nodes.py` — replace `transform_text` with `analyze_data`; add `handle_error`, `finalize`
- `src/graph/state.py` — extend AgentState with `dataset_id`, `question`, `chart_type`, `labels`, `values`, `summary`
- `src/graph/graph.py` — StateGraph assembly with conditional edges
- `src/api/datasets.py` — new: POST /datasets, GET /datasets
- `src/api/analyze.py` — new: POST /analyze (invokes LangGraph runner)
- `src/domain/dataset.py` — new: pandas parsing, schema extraction, sample rows
- `src/domain/analysis.py` — new: analysis result Pydantic model
- `src/db/models.py` — add Dataset model; extend Run model with dataset_id, question, chart_type
- `alembic/versions/0002_add_datasets.py` — new migration: creates datasets table, adds columns to runs
- `src/prompts/analyze.md` — replaces `src/prompts/transform.md`
- `src/config/settings.py` — add AGENT_GEMINI_API_KEY, AGENT_LLM_MODEL settings
- `tests/integration/test_pipeline.py` — end-to-end test: upload fixture CSV → analyze → assert chart_type, labels, values, summary
- `tests/fixtures/sales.csv` — fixture CSV with at least 25 rows (month, product, revenue) — enough that a sampled 20-row answer and a full-data answer are observably different
- `pyproject.toml` — add pandas>=2.2, openpyxl>=3.1 to [project.dependencies]

slice-b owns:
- `frontend/src/app/page.tsx` — full page: Header, DataSourcePanel, FileUploadDropzone, ChatInput, ResultsArea, DatabaseModal
- `frontend/package.json` — add recharts ^2.12

True dependency: slice-b does not need slice-a's output to build. Both slices build concurrently. The integration test in slice-a requires a running backend (handled by the test fixture), not slice-b.

**Gate command:**
```
uv run alembic upgrade head && uv run pytest tests/integration/test_pipeline.py -v
```
Runs against the real Gemini API (`AGENT_GEMINI_API_KEY` from `.env`) and the production SQLite driver. The test uploads `tests/fixtures/sales.csv` (25+ rows) and asks a question; it asserts that `chart_type` is a non-empty string, `labels` has at least 3 items, `values` has at least 3 items (matching `labels` length), and `summary` is a non-empty string. The fixture has enough rows (25+) that a query aggregating by month produces a different answer on 20 rows vs all rows — proving real execution, not sample pass-through.

**How the user tests it:**
1. Ensure `.env` contains `AGENT_GEMINI_API_KEY=<your key>`
2. `cd frontend && pnpm build` (one-time after slice-b is built)
3. `uv run python -m src` — starts server on port 8001
4. Open `http://localhost:8001/app/`
5. Drag any CSV (or use `tests/fixtures/sales.csv`) onto the dropzone
6. See filename + column list + row count appear (e.g. "Columns: month, product, revenue | 25 rows")
7. Type "Show me revenue by month as a bar chart" and click Analyze
8. See a bar chart rendered with real monthly revenue data from the file
9. See a written summary paragraph below the chart
10. Click "Connect Database (Phase 2)" button — a modal appears: "PostgreSQL database connection is coming in Phase 2. Stay tuned!" — close it with the X button
11. The "Connect Database" button reads "(Phase 2)" — clearly a labelled stub, not a broken feature

Real on the tested path: upload, POST /datasets, POST /analyze, LangGraph graph, Gemini call, pandas execution, Recharts chart, summary card.

Labelled stubs: "Connect Database (Phase 2)" button + modal.

---

### Phase 2 — PostgreSQL Data Source

**Goal:** Wire the Phase 1 "Connect Database" stub into real PostgreSQL connectivity. User can enter a Postgres connection string (or use `AGENT_PG_URL` from `.env`), browse tables, and ask the same NL questions against live DB data — receiving the same chart + summary output.

**Independent slices (parallel build units):**

- `slice-a` (backend) — Postgres connection validation endpoint, table schema introspection, SQL generation node (Gemini writes SQL instead of pandas code), query execution, Phase 2 migration. No dependency on slice-b.
- `slice-b` (frontend) — Wire the "Connect Database" tab: connection string form (or auto-load AGENT_PG_URL), table browser, reuse existing ChatInput + ResultsArea. No dependency on slice-a.

**Key surfaces / files:**

slice-a: `src/api/databases.py`, `src/graph/nodes.py` (add `analyze_db` node), `src/config/settings.py` (add `AGENT_PG_URL`), `alembic/versions/0003_phase2.py`, `tests/integration/test_pg_pipeline.py`

slice-b: `frontend/src/app/page.tsx` (wire ConnectDatabaseButton tab into real form + table browser)

**Gate command:**
```
uv run pytest tests/integration/test_pg_pipeline.py -v
```
Requires `AGENT_PG_URL` and `AGENT_GEMINI_API_KEY` in `.env`. Connects to real Postgres, introspects a table, runs NL analysis, asserts chart output.

**How the user tests it:** Fill `AGENT_PG_URL` in `.env`, start the server, click "Connect Database", enter connection string, select a table, ask a question, see a chart from live DB data.

---

### Phase 3 — Agentic Stack Upgrade + Resilience

**Goal:** Harden all external calls with error handling, retries, and timeouts. The agent degrades gracefully (returns a clear error) rather than crashing on Gemini API errors or pandas execution timeouts.

**Independent slices (parallel build units):**

- `slice-a` (backend) — try/except + exponential-backoff retry on Gemini calls (max 3 attempts), timeout on pandas exec (30s), structured error responses, error-path integration tests

**Gate command:**
```
uv run pytest -v
```
All tests pass including error-path tests that mock Gemini failures and assert the agent returns HTTP 500 with a structured error (not an unhandled exception).

---

### Phase 4 — Complete Agentic System

**Goal:** All stubs replaced with real functionality, the full system runs end-to-end, and a spec-to-code drift audit is clean.

**Gate command:**
```
uv run pytest -v
```
All tests pass; qa-auditor drift audit reports zero spec-to-code divergences.
