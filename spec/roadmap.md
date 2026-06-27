# Roadmap

DataChat — a personal, local data-analysis agent. Upload a spreadsheet (or connect a database), ask a question in plain English, get a plain-English answer plus a chart — with your raw data never leaving your machine.

---

## What This Agent Does

DataChat lets one person explore their own data conversationally. The user opens a local web app, uploads a CSV/spreadsheet (or, from Phase 2, connects a PostgreSQL database), and types questions in plain English ("which region had the highest revenue last quarter?", "show me sales by month"). DataChat answers in plain English and renders a chart or visual summary when the question is quantitative. The defining property is privacy: **raw data rows never leave the machine.** All row-level computation runs locally; only the dataset's schema (column names + types) and small computed aggregates / summary statistics are ever sent to the LLM, which reasons over that summary to phrase the answer and choose the chart.

## Who Uses It

A single individual — an analyst, founder, researcher, or operator — running the tool on their own laptop for on-demand, personal analysis. They are comfortable uploading a file or pasting a database connection string but do not want to write SQL or pandas, and are unwilling to upload sensitive rows to a cloud service. There is no multi-user, auth, or sharing concern; it is a personal local tool.

## Core Problem Being Solved

Answering ad-hoc questions about your own data today means either (a) writing SQL/pandas yourself, or (b) pasting the data into a cloud LLM chat — which leaks sensitive rows and is the dealbreaker. DataChat removes both: it gives the conversational ease of an LLM analyst while guaranteeing the rows stay local, and it connects to the tools the user already has (spreadsheets, PostgreSQL).

## Success Criteria

- [ ] A user can upload a CSV at `http://localhost:8001/app/`, ask a plain-English question, and receive a correct plain-English answer plus a chart within one interaction.
- [ ] The answer is computed over the **full dataset locally** (DuckDB/pandas), not over a sample — a question whose answer differs between a sample and the full data returns the full-data answer.
- [ ] **No raw data row is ever sent to the LLM.** Only schema + computed aggregates cross the boundary; this is enforced in code at a single named surface and proven by a test.
- [ ] The agent runs entirely locally (FastAPI + Next.js single origin), using Gemini 2.5 Flash for reasoning, with frugal LLM usage (at most a small bounded number of calls per question).
- [ ] From Phase 2, the user can connect a PostgreSQL database via a connection string and ask the same questions with the same privacy guarantee.

## What This Agent Does NOT Do (Out of Scope)

- No multi-user support, accounts, authentication, or sharing — single local user only.
- No cloud deployment, hosting, or remote access — local single-origin app only.
- No writing back to the user's data sources — read-only analysis.
- No sending raw rows, individual records, or full columns to the LLM under any circumstance.
- No automated scheduled reports, alerts, or background jobs (on-demand only).
- No support for data sources beyond CSV/spreadsheet (Phase 1) and PostgreSQL (Phase 2) — no Snowflake/BigQuery/APIs in scope.
- No fine-tuning, model training, or learning from user data.

## Key Constraints

- **Privacy boundary (hard, non-negotiable):** raw rows stay on the machine; only schema + aggregates reach the LLM. Enforced in code, not just documented. See [architecture.md → Privacy Boundary](architecture.md#privacy-boundary-first-class-constraint) and [agent.md → Privacy Boundary Enforcement](agent.md#privacy-boundary-enforcement).
- **Cost:** Gemini 2.5 Flash (`gemini-2.5-flash`), frugal — a bounded small number of LLM calls per question (target ≤ 2: one to plan the local computation, one to phrase the answer; aim for 1 where possible).
- **Local-only:** single-origin FastAPI + Next.js static export at `http://localhost:8001/app/`; the app's own metadata store is SQLite (this is the app store, not the analysed data).
- **Compute locality:** all row-level work runs locally via DuckDB (with pandas where convenient); the analysed data is never persisted beyond the user's session needs and never transmitted.

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** It covers the primary requirements with depth — upload → ask → answer + chart, with the privacy boundary actually enforced. Frontend is visually complete with clearly-labelled NON-FUNCTIONAL stubs for later features. Each later phase wires a stub into real functionality.

### Phase 1 — First Delight: Upload → Ask → Answer + Chart (privacy enforced)

- **Goal:** The user uploads a CSV at `http://localhost:8001/app/`, types a plain-English question, and gets BOTH a plain-English answer AND a chart — computed over the full dataset locally, with only schema + aggregates sent to Gemini 2.5 Flash. The LangGraph agentic stack drives this path end to end.
- **Independent slices (parallel build units):**
  - `db-metadata` (backend) — Alembic migration + SQLAlchemy models for `Dataset` and `Question` metadata rows; settings additions (`upload_dir`). deps: none.
  - `local-compute` (backend) — DuckDB/pandas ingestion of an uploaded CSV into a local table; schema profiling and the aggregate/summary builder; **the privacy boundary surface** (`src/tools/profile.py` + `src/tools/compute.py`). deps: none.
  - `agent-graph` (backend) — repurpose the `transform_text` slot into the DataChat graph: state extension, nodes (profile → plan → local-execute → phrase+chart), edges, prompt files; integrate `local-compute` outputs. deps: `local-compute` (consumes its functions — serialize this one after local-compute).
  - `api-routes` (backend) — `POST /datasets` (upload), `POST /ask`, `GET /health` routers returning `ok()`/`api_error()` envelopes; wire into `create_app()`. deps: `agent-graph`, `db-metadata` (calls the runner + persists rows — serialize after those).
  - `frontend` (frontend) — single page: upload control, chat box, answer panel, chart render (chart lib), and clearly-labelled NON-FUNCTIONAL stubs (PostgreSQL connect, multi-dataset switcher, downloadable report, anomaly detection). deps: none (builds against the documented API contract in [api.md](api.md)).
- **Key surfaces / files:**
  - `db-metadata`: `src/db/models.py`, `alembic/versions/0002_datasets_questions.py`, `src/config/settings.py`
  - `local-compute`: `src/tools/profile.py`, `src/tools/compute.py`, `src/tools/duckdb_store.py`
  - `agent-graph`: `src/graph/state.py`, `src/graph/nodes.py`, `src/graph/edges.py`, `src/graph/agent.py`, `src/graph/runner.py`, `src/prompts/plan.md`, `src/prompts/answer.md` (rename/remove `src/prompts/transform.md`)
  - `api-routes`: `src/api/datasets.py`, `src/api/ask.py`, `src/api/__init__.py`, `src/domain/dataset.py`, `src/domain/ask.py`
  - `frontend`: `frontend/src/app/page.tsx`, `frontend/src/app/components/*`, `frontend/package.json`
- **Gate command:** `uv run alembic upgrade head && uv run pytest tests/phase1 -q` — runs against the real Gemini API using `AGENT_GEMINI_API_KEY` from `.env` and the production SQLite app store (SQLite IS the production app store here, not a substitute). The phase-1 suite includes `tests/phase1/test_privacy_boundary.py` (asserts only schema + aggregates reach the LLM payload), `tests/phase1/test_full_data.py` (fixture large enough that a sampled answer differs from the full-data answer — proves full-data compute), and `tests/phase1/test_pipeline.py` (real Gemini run: upload → ask → answer + chart spec).
- **How the user tests it (handoff seed):**
  1. Set `AGENT_GEMINI_API_KEY` in `.env`; run `python agent.py --run`.
  2. Open `http://localhost:8001/app/`.
  3. Upload a CSV (e.g. sales data). Confirm the column list / row count appears (real).
  4. Type "what is total revenue by region?" and submit. Expect a plain-English answer AND a bar chart (real, computed locally).
  5. Labelled stubs (visibly marked "Coming soon", non-clickable or showing a notice): **Connect PostgreSQL**, **Switch dataset / multi-dataset**, **Download report**, **Detect anomalies**. These are intentionally non-functional — not bugs.

### Phase 2 — Live PostgreSQL Connection

- **Goal:** The user pastes a PostgreSQL connection string, DataChat introspects the schema, and the user asks the same questions — with row-level computation running locally (DuckDB scanning Postgres) and only schema + aggregates sent to the LLM. Wires the "Connect PostgreSQL" Phase-1 stub into real functionality.
- **Independent slices (parallel build units):**
  - `pg-connect` (backend) — connection-string handling, schema introspection, DuckDB `postgres_scanner` setup so aggregates compute locally over the live DB; settings for an optional default connection string. deps: none.
  - `source-routing` (backend) — extend the graph profile/compute nodes to accept a source = CSV dataset OR Postgres connection; reuse the same aggregate/boundary surface. deps: `pg-connect`.
  - `api-pg` (backend) — `POST /connections` (register + validate a connection string), extend `POST /ask` to target a connection. deps: `pg-connect`, `source-routing`.
  - `frontend-pg` (frontend) — turn the "Connect PostgreSQL" stub into a real form (connection string input, validate, then ask against it). deps: none (builds against [api.md](api.md)).
- **Key surfaces / files:** `src/tools/pg_source.py`, `src/tools/duckdb_store.py`, `src/graph/nodes.py`, `src/api/connections.py`, `src/api/ask.py`, `src/db/models.py` (+ migration `0003_connections`), `frontend/src/app/components/ConnectPostgres.tsx`
- **Gate command:** `uv run alembic upgrade head && uv run pytest tests/phase2 -q` — real Gemini via `.env`; a local throwaway PostgreSQL instance for the source (the analysed source); the app store remains SQLite. `tests/phase2/test_pg_privacy.py` asserts no rows from the Postgres source appear in the LLM payload; `tests/phase2/test_pg_pipeline.py` runs upload-free ask against a seeded Postgres table.
- **How the user tests it (handoff seed):** Open `http://localhost:8001/app/`, click "Connect PostgreSQL", paste a connection string, validate, then ask "average order value by customer segment". Expect answer + chart computed from the live DB with rows never leaving the machine. CSV upload still works unchanged.

### Phase 3 — Charts Depth + Downloadable Report

- **Goal:** Richer visualization (chart-type selection appropriate to the question: bar / line / pie / table) and a downloadable plain-English + chart report of the current answer. Wires the "Download report" stub.
- **Independent slices (parallel build units):**
  - `chart-spec` (backend) — extend the answer node to emit a richer chart spec (type chosen from the data shape) within the same frugal call budget. deps: none.
  - `report-export` (backend) — `GET /questions/{id}/report` producing a self-contained HTML report (answer text + embedded chart data) generated locally. deps: none.
  - `frontend-charts` (frontend) — render the chosen chart type; wire the "Download report" button to the report endpoint. deps: none (against [api.md](api.md)).
- **Key surfaces / files:** `src/graph/nodes.py`, `src/prompts/answer.md`, `src/api/reports.py`, `frontend/src/app/components/ChartPanel.tsx`, `frontend/src/app/components/DownloadReport.tsx`
- **Gate command:** `uv run pytest tests/phase3 -q` — real Gemini via `.env`; asserts chart-type selection varies with question shape and the report endpoint returns a valid self-contained document.
- **How the user tests it (handoff seed):** Ask a trend question ("revenue over time") → expect a line chart; ask a share question ("revenue share by region") → expect a pie/bar; click "Download report" → an HTML file downloads with the answer and chart. No raw rows in the report metadata sent anywhere.

### Phase 4 — Agentic Stack Upgrade + Resilience

- **Goal:** Promote the Phase-1 base loop to the production agentic architecture in [agent.md](agent.md): conversational memory across turns (follow-up questions reuse prior context), reflection on the local-compute plan (self-check the proposed aggregation against the schema before executing), guardrails on LLM-produced compute plans, and exception handling on every external call.
- **Independent slices (parallel build units):**
  - `memory` (backend) — per-conversation turn memory in `AgentState.messages` persisted to the app store; follow-ups resolve references ("and by month?"). deps: none.
  - `reflection-guardrails` (backend) — a validation pass on the LLM's proposed compute plan (columns exist, aggregation is well-formed, no raw-row leakage) before local execution; reject + re-plan once on failure. deps: none.
  - `resilience` (backend) — retries/backoff/timeouts around the Gemini call and DuckDB/Postgres execution; graceful degraded responses instead of crashes. deps: none.
- **Key surfaces / files:** `src/graph/nodes.py`, `src/graph/edges.py`, `src/graph/state.py`, `src/tools/compute.py`, `src/llm/client.py`, `src/db/models.py` (+ migration `0004_conversation`)
- **Gate command:** `uv run pytest tests/phase4 -q` — real Gemini via `.env`; tests cover a multi-turn follow-up that depends on prior context, a malformed-plan rejection + re-plan, and an injected Gemini-timeout degraded path.
- **How the user tests it (handoff seed):** Ask "total revenue by region", then "now just for last year" (a follow-up) → expect the agent to use prior context. Force a bad question and confirm a clear non-crashing message.

### Phase 5 — Complete Agentic System + Anomaly Detection

- **Goal:** All capabilities real with no stubs on any active path; wire the final "Detect anomalies" stub into a real local anomaly-spotting pass (computed locally; only summary statistics of flagged points reach the LLM for phrasing). The full agentic graph in [agent.md](agent.md) is active and matches the running code.
- **Independent slices (parallel build units):**
  - `anomaly-compute` (backend) — local anomaly detection (e.g. z-score / IQR over a chosen numeric column via DuckDB); only summary stats of outliers cross to the LLM. deps: none.
  - `anomaly-graph` (backend) — an anomaly branch in the graph + prompt for phrasing the finding. deps: `anomaly-compute`.
  - `frontend-anomaly` (frontend) — turn the "Detect anomalies" stub into a real control + result panel. deps: none (against [api.md](api.md)).
- **Key surfaces / files:** `src/tools/anomaly.py`, `src/graph/nodes.py`, `src/graph/edges.py`, `src/prompts/anomaly.md`, `src/api/ask.py`, `frontend/src/app/components/AnomalyPanel.tsx`
- **Gate command:** `uv run pytest tests/phase5 -q` — real Gemini via `.env`; full end-to-end across CSV and Postgres sources; a drift check that the graph topology matches [agent.md](agent.md); anomaly privacy test (no raw rows in payload).
- **How the user tests it (handoff seed):** Upload data with a known outlier, click "Detect anomalies", and confirm the flagged point(s) are described in plain English with a chart highlighting them. Confirm every previously-stubbed control is now real.
