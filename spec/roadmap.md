# Roadmap

## What This Agent Does

The Data Analyst Agent lets users upload CSV and Excel files through a web interface, asks natural-language questions about the data, and receives formatted text answers plus HTML tables backed by real SQL. Internally it follows a senior-analyst workflow: Gemini plans the SQL using structured tool-use, the executor runs it against SQLite, and the formatter assembles a markdown + table response. Every SQL and data operation is written to an audit log that is itself queryable through the UI. Each visitor gets an isolated workspace namespaced by a browser-generated session ID — no login required.

## Who Uses It

Data analysts, product managers, and non-technical stakeholders who need to explore CSV/Excel exports without writing SQL or setting up a local database. Their goal: ask plain-English questions and get answers in seconds.

## Core Problem Being Solved

Exploring CSV/Excel data today requires either SQL knowledge and a database tool, or expensive cloud BI services. This agent removes both barriers: upload a file, ask a question, get an answer — fully local, no data leaves the machine except the Gemini API call.

## Success Criteria

- [ ] A user can upload a CSV or Excel file and see it listed in the sidebar within 5 seconds
- [ ] A natural-language question returns a correct SQL-backed answer (text + table) within 15 seconds on gemini-2.5-flash
- [ ] Every SQL execution appears in the audit log with session_id, query, row_count, and duration_ms
- [ ] Two browser tabs with different session IDs cannot see each other's datasets
- [ ] The app runs entirely locally (only outbound connection: Gemini API)

## What This Agent Does NOT Do (Out of Scope)

- Connect to external databases (PostgreSQL, MySQL, BigQuery, etc.)
- Send data to any service other than the Gemini API
- Authenticate users or persist sessions beyond a browser reset
- Schedule or automate recurring queries
- Export results as new files
- Support SQL dialects other than SQLite

## Key Constraints

- SQLite only — no external DB connections
- Fully local — no outbound connections except the Gemini API (AGENT_GEMINI_API_KEY)
- All settings use the AGENT_ env prefix
- DB path: ./data/agent.db
- Dev port: 8001
- Multi-user isolation: session_id namespaced table names ({session_id}_{dataset_name})

---

## Phases of Development

> Phase 1 is the smallest first-time-right user-testable win. It must work perfectly on the first try — zero rough edges on the tested path. Backend is minimal but REAL. Frontend is visually complete with clearly-labelled stubs for unbuilt phases.

---

### Phase 1 — Upload + NL Query (Core Path)

**Goal:** A user uploads a CSV or Excel file, asks a natural-language question, and receives a formatted text + table answer backed by real Gemini-generated SQL. The audit log records the event. Charts and Dashboards panels are visible but labelled stubs.

**Independent slices (parallel build units):**

- `slice-backend` (backend) — ALL backend work: Alembic migrations for sessions/datasets/audit_log tables; dataset ingestion (CSV/Excel → dynamic SQLite table, POST /datasets/upload, GET /datasets); NL→SQL pipeline (LangGraph graph: query_planner → sql_executor → response_formatter → audit_logger, POST /query); GET /audit endpoint; GET /health; multi-user session isolation. Surfaces: src/db/models.py, src/config/settings.py, src/ingest/parser.py, src/ingest/loader.py, src/graph/state.py, src/graph/nodes.py, src/graph/agent.py, src/graph/edges.py, src/api/datasets.py, src/api/query.py, src/api/audit.py, src/api/health.py, src/api/__init__.py, src/__main__.py, src/llm/providers/gemini.py, src/prompts/query_planner.md, alembic/versions/001_initial.py; tests: tests/unit/, tests/integration/

- `slice-frontend` (frontend) — full Next.js UI: sidebar (dataset list + upload button), chat-style query input + response panel, Audit tab (calls GET /audit), Charts stub card, Dashboards stub card, session ID in footer sent as X-Session-ID header on every call. Surfaces: frontend/src/app/page.tsx, frontend/src/app/layout.tsx, frontend/src/components/Sidebar.tsx, frontend/src/components/QueryPanel.tsx, frontend/src/components/AuditTab.tsx, frontend/src/components/StubCard.tsx, frontend/postcss.config.mjs

**Key surfaces / files:**

| Slice | Owns |
|-------|------|
| slice-backend | src/db/models.py, src/graph/nodes.py, src/graph/agent.py, src/api/datasets.py, src/api/query.py, src/api/audit.py |
| slice-frontend | frontend/src/app/page.tsx, frontend/src/components/Sidebar.tsx, frontend/src/components/QueryPanel.tsx, frontend/src/components/AuditTab.tsx |

**Gate command:**
```
uv run alembic upgrade head && uv run pytest tests/ -x -q
```
Runs against the real Gemini API (AGENT_GEMINI_API_KEY in .env) and the SQLite DB at ./data/agent.db.

**How the user tests it:**
1. From repo root: `cd frontend && pnpm build && cd .. && uv run python -m src`
2. Open `http://localhost:8001/app/` in a browser
3. Click "Upload" in the left sidebar, pick any .csv or .xlsx file — the file should appear in the dataset list within 5 seconds
4. Type a natural-language question about the dataset in the chat input (e.g. "What are the top 5 values in the first column?") and press Send
5. A formatted answer (text + table) should appear in the response panel
6. Click the "Audit" tab — a table of logged SQL operations should appear
7. The "Charts" and "Dashboards" cards are visible with labels "Charts — coming in Phase 2" and "Dashboards — coming in Phase 3" — these are expected stubs, not bugs

---

### Phase 2 — Charts in Responses

**Goal:** Query responses optionally include a bar, line, or pie chart rendered by the frontend charting library. The backend returns chart-ready data; the frontend renders it.

**Independent slices (parallel build units):**

- `slice-chart-backend` (backend) — extend POST /query response to include chart_data: {type, labels, values} when the result set is chart-renderable (numeric column + label column); extend response_formatter node; deps: none
- `slice-chart-frontend` (frontend) — replace Charts stub card with real chart component (Recharts); render chart_data from query response inline in the response panel; deps: none

**Key surfaces / files:**

| Slice | Owns |
|-------|------|
| slice-chart-backend | src/graph/nodes.py (response_formatter), src/api/query.py |
| slice-chart-frontend | frontend/src/components/ChartPanel.tsx, frontend/src/components/QueryPanel.tsx |

**Gate command:**
```
uv run pytest tests/ -x -q
```

**How the user tests it:**
1. Start the app: `cd frontend && pnpm build && cd .. && uv run python -m src`
2. Open `http://localhost:8001/app/`
3. Upload a CSV with numeric columns, ask "Show me a bar chart of sales by region"
4. A bar chart appears below the text answer
5. The Dashboards card still shows "Dashboards — coming in Phase 3" stub

---

### Phase 3 — Pinned Dashboards

**Goal:** Users can save queries (with their charts) to a named dashboard, then revisit and refresh them.

**Independent slices (parallel build units):**

- `slice-dashboard-db` (backend) — Alembic migration for dashboards and dashboard_items tables; deps: none
- `slice-dashboard-api` (backend) — POST /dashboards, GET /dashboards, GET /dashboards/{id}, DELETE /dashboards/{id}/items/{item_id}; deps: slice-dashboard-db
- `slice-dashboard-frontend` (frontend) — replace Dashboards stub with real Dashboards panel: create/list/view dashboards, pin query+chart to a dashboard; deps: none

**Key surfaces / files:**

| Slice | Owns |
|-------|------|
| slice-dashboard-db | alembic/versions/003_dashboards.py, src/db/models.py |
| slice-dashboard-api | src/api/dashboards.py |
| slice-dashboard-frontend | frontend/src/components/DashboardsPanel.tsx |

**Gate command:**
```
uv run pytest tests/ -x -q
```

**How the user tests it:**
1. Start the app: `cd frontend && pnpm build && cd .. && uv run python -m src`
2. Run a query, click "Pin to Dashboard", name the dashboard
3. Navigate to the Dashboards tab — the pinned query + chart appears
4. Click "Refresh" — the query re-runs and updates the result

---

### Phase 4 — Audit Log UI

**Goal:** The audit log is browsable and filterable through a dedicated UI view in the app.

**Independent slices (parallel build units):**

- `slice-audit-filter-api` (backend) — extend GET /audit with query params: dataset_table, from_date, to_date, limit, offset; deps: none
- `slice-audit-frontend` (frontend) — replace basic audit table with full Audit UI: filter bar, pagination, detail drawer showing full SQL + row_count + duration; deps: none

**Key surfaces / files:**

| Slice | Owns |
|-------|------|
| slice-audit-filter-api | src/api/audit.py |
| slice-audit-frontend | frontend/src/components/AuditTab.tsx, frontend/src/components/AuditDetailDrawer.tsx |

**Gate command:**
```
uv run pytest tests/ -x -q
```

**How the user tests it:**
1. Start the app: `cd frontend && pnpm build && cd .. && uv run python -m src`
2. Run several queries, click the "Audit" tab
3. Filter by dataset name — only matching rows appear
4. Click any row — a detail drawer opens showing the full SQL, row count, and duration
