# Roadmap

## What This Agent Does

A personal, fully-local data analysis tool. The user uploads CSV or Excel files via a browser chat UI; each file is immediately parsed into a named SQLite table. The user then asks natural-language questions about the data. The agent generates SQL, executes it, computes descriptive statistics and anomaly detection in Python, calls Gemini to produce a 150-300 word prose narrative, auto-selects up to 4 chart types, and returns the full result — SQL used, prose narrative, and inline charts — directly in the chat thread. Everything runs on the user's machine; no data is sent to cloud storage.

## Who Uses It

A single technical user (the developer / data analyst who set up the tool) who wants to do ad-hoc exploration of CSV/Excel data without writing SQL manually or standing up a BI tool. They upload a file, ask questions in plain English, and see structured prose and charts immediately.

## Core Problem Being Solved

Ad-hoc data exploration requires either writing SQL by hand, using a cloud BI tool (data leaves the machine), or using a general-purpose LLM chat interface that can't execute queries against uploaded files. This tool eliminates all three frictions: no SQL required, fully local, immediate results with charts.

## Success Criteria

- [ ] Uploading a CSV file and asking "What is the average revenue by region?" returns a correct SQL query, a prose narrative with accurate statistics, and at least one chart — within 30 seconds on a modern laptop.
- [ ] A repeated question (same session, same tables) returns the cached result without an additional Gemini API call (verified by checking `analysis_cache` row count).
- [ ] A dataset with 100 000 rows is ingested in under 10 seconds and the first question returns a result.
- [ ] A file upload of 60 MB returns HTTP 413 without crashing the server.
- [ ] The `insight_json.anomalies` field correctly identifies a synthetic outlier (value injected more than 3 std devs from the mean) in a test CSV.

## What This Agent Does NOT Do (Out of Scope)

- Write or mutate data (no INSERT/UPDATE/DELETE — SELECT only).
- Connect to external databases (PostgreSQL deferred to Phase 4).
- Persist conversation history across page reloads (Phase 2).
- Export results to CSV or other formats (Phase 4; stub labelled "Coming Later" visible in Phase 1 UI).
- Authenticate users or enforce access control (personal local tool; localhost only).
- Send uploaded data to cloud storage (ever — this is a hard constraint).
- Generate charts server-side; charts are rendered client-side only via Recharts.
- Handle files larger than 50 MB or datasets with more than 500 000 rows.

## Key Constraints

- **Fully local:** all data stays on disk; only prompt text (schema context + statistics JSON) is sent to Gemini.
- **LLM cost minimization:** cache query results by `(question_hash, table_hash)`; send schema context (capped at 20 sample rows per table) and statistics JSON (not raw rows) to the LLM.
- **SQLite only (Phase 1-3):** no PostgreSQL driver needed; aiosqlite is also excluded (sync ORM throughout).
- **Port 8001:** as mandated by `harness/patterns/tech-stack.md`.
- **Extend skeleton in place:** all code goes into the existing `src/` and `frontend/` trees; no new directories at the repo root level.

---

## Phases of Development

### Phase 1 — First Delight: Upload, Ask, See Results

**Goal:** A user can upload a CSV or Excel file, ask a natural-language question, and immediately see a SQL query, a prose narrative with key metrics and trends, and up to 4 inline charts — all running against the real Gemini API from `.env`.

**Independent slices (parallel build units):**

- `slice-a` (backend) — DB migration, models, ingest endpoint, analysis graph (all 6 nodes), analysis endpoint, runner extension. Owns: `src/`, `alembic/versions/0002_data_analysis.py`, `tests/`. Deps: none.
- `slice-b` (frontend) — Full chat UI with file drop zone, chat history, SQL disclosure, prose narrative, Recharts inline charts, loading states, error states, Phase 2 stubs. Owns: `frontend/src/`. Deps: none (mocks API responses during development; real integration tested via TestClient).

**Key surfaces / files:**

Slice A (backend):
- `alembic/versions/0002_data_analysis.py` — new migration
- `src/db/models.py` — extend `RunRow`; add `SessionRow`, `UploadedFileRow`, `AnalysisCacheRow`
- `src/db/session.py` — add WAL mode pragma
- `src/graph/state.py` — replace `AgentState` with `AnalysisState`
- `src/graph/nodes.py` — replace `transform_text` with `generate_sql`, `execute_sql`, `generate_insights`, `generate_charts`, `handle_error`, `finalize`
- `src/graph/edges.py` — replace `after_transform` with four edge functions
- `src/graph/agent.py` — replace graph wiring per `spec/agent.md`
- `src/graph/runner.py` — extend `run_agent` to accept `session_id` + `question`
- `src/api/sessions.py` — new router: `POST /sessions`, `POST /sessions/{id}/files`, `GET /sessions/{id}/files`, `POST /sessions/{id}/analyze`
- `src/api/__init__.py` — register `sessions` router
- `src/domain/session.py` — Pydantic request/response models
- `src/prompts/generate_sql.md` — SQL generation system prompt
- `src/prompts/generate_insights.md` — prose narrative system prompt
- `src/ingest/file_ingest.py` — pandas parse + SQLite `to_sql` + column sanitization
- `tests/test_phase1_backend.py` — unit tests for each node + integration test (full graph, real Gemini, real CSV with 200 rows)
- `pyproject.toml` — add `pandas>=2.2`, `openpyxl>=3.1`

Slice B (frontend):
- `frontend/src/app/page.tsx` — replace transform form with full two-column layout
- `frontend/src/components/FileDropZone.tsx` — drag-drop upload widget
- `frontend/src/components/TablePills.tsx` — ingested table badges
- `frontend/src/components/ChatThread.tsx` — chat message list
- `frontend/src/components/AgentMessage.tsx` — SQL disclosure + prose + charts
- `frontend/src/components/ChartPanel.tsx` — Recharts dispatcher
- `frontend/src/components/MessageInput.tsx` — question input + submit
- `frontend/package.json` — add `recharts`

**Gate command:**
```
uv run alembic upgrade head && uv run pytest tests/test_phase1_backend.py -v
```

The integration test in `tests/test_phase1_backend.py` uploads a synthetic CSV with 200 rows (10 numeric columns, 1 date column, 1 categorical column, with one injected outlier), sends a real question to `POST /sessions/{id}/analyze`, and asserts:
- `status == "completed"`
- `sql_query` is a non-empty string containing `SELECT`
- `insight_json.numeric_columns` is non-empty and each entry has `min`, `max`, `mean`
- `insight_json.anomalies` is non-empty (the injected outlier is detected)
- `chart_specs` has at least 1 entry with `chart_type` in `{line, bar, histogram, scatter}`
- `output_text` is between 50 and 600 characters

The 200-row CSV ensures sample (20 rows) and full data (200 rows) produce observably different statistics, validating that the full execution path runs correctly.

**How the user tests it (handoff seed):**

1. Ensure `.env` contains `AGENT_GEMINI_API_KEY=<your-key>`.
2. Run migrations: `uv run alembic upgrade head`
3. Build frontend: `cd frontend && pnpm build`
4. Start server: `cd .. && uv run python -m src`
5. Open `http://localhost:8001/app/`
6. Drag a CSV file onto the drop zone in the left sidebar. Expect a green pill badge to appear with the table name and row count.
7. Type "What is the average value per category?" in the message input and click Analyze.
8. Expect: a user bubble with the question, then an agent bubble containing (a) a collapsible "SQL used" section, (b) a prose paragraph, (c) at least one inline chart.

Real on the tested path: file upload, SQL generation (real Gemini), SQL execution, statistics computation, prose narrative (real Gemini), chart spec generation, chart rendering.

Labelled stubs: PostgreSQL connection panel (sidebar bottom, greyed out — "Coming in Phase 2"), Export button (top-right, disabled — "Coming Later").

---

### Phase 2 — Caching and Conversation History

**Goal:** Repeated questions return cached results without LLM calls; conversation history persists across page reloads for the same session.

**Independent slices (parallel build units):**

- `slice-a` (backend) — Wire `analysis_cache` (the table exists from Phase 1 migration but cache lookup is skipped in Phase 1 runner; Phase 2 adds the cache-hit path in `runner.py`). Add `GET /sessions/{id}/history` endpoint returning all runs for a session ordered by `created_at`. Deps: none.
- `slice-b` (frontend) — On page load, re-fetch session history from `GET /sessions/{id}/history` and restore the chat thread. Deps: none.

**Key surfaces / files:**

Slice A: `src/graph/runner.py` (add cache lookup before graph invocation), `src/api/sessions.py` (add history endpoint), `tests/test_phase2_cache.py`

Slice B: `frontend/src/app/page.tsx` (restore history on mount), `frontend/src/components/ChatThread.tsx` (handle restored messages)

**Gate command:**
```
uv run pytest tests/test_phase2_cache.py -v
```

The test asks the same question twice in the same session with the same tables; asserts that `analysis_cache` has exactly 1 row after both calls (cache hit on second call) and that both runs return identical `sql_query` and `insight_json`.

**How the user tests it:** Reload the page — the previous question and answer should be restored. Ask the same question again — it should return instantly (cached).

---

### Phase 3 — Agentic Stack Upgrade and Resilience

**Goal:** Retry logic on Gemini calls; reflection node that regenerates SQL if execution returns an error; all `spec/agent.md` patterns active and tested.

**Independent slices:**

- `slice-a` (backend) — Add exponential backoff retry (max 3 attempts) to `generate_sql` and `generate_insights` Gemini calls. Add a `reflect_sql` node: if `execute_sql` encounters a SQL error, `reflect_sql` sends the error + original SQL back to Gemini to regenerate (max 1 retry). Wire `reflect_sql` as an optional edge from `execute_sql`. Deps: none.
- Slice B: no frontend changes for this phase.

**Key surfaces / files:** `src/graph/nodes.py`, `src/graph/edges.py`, `src/graph/agent.py`, `tests/test_phase3_resilience.py`

**Gate command:**
```
uv run pytest tests/test_phase3_resilience.py -v
```

Tests: (a) Gemini call that fails once then succeeds — verify the run completes; (b) SQL that is syntactically invalid — verify `reflect_sql` fires and the corrected SQL executes successfully.

---

### Phase 4 — Complete Agentic System and PostgreSQL

**Goal:** PostgreSQL connectivity available from the UI; all spec capabilities fully real (no stubs); complete drift audit passes.

**Independent slices:**

- `slice-a` (backend) — Add `POST /connections` and `GET /connections/{id}/tables` endpoints for registering a PostgreSQL connection string. Extend the `generate_sql` node to query tables from the registered PostgreSQL connection in addition to SQLite uploaded tables. Deps: none.
- `slice-b` (frontend) — Wire the PostgreSQL connection panel stub into a real form that calls `POST /connections`. Remove the "Coming in Phase 2" label from the Export button and implement CSV export from `insight_json`. Deps: none.

**Key surfaces / files:** `src/api/connections.py`, `src/db/models.py` (add `ConnectionRow`), `src/graph/nodes.py` (extend `generate_sql`), `frontend/src/components/` (PostgreSQL form, export), `alembic/versions/0003_connections.py`

**Gate command:**
```
uv run alembic upgrade head && uv run pytest -v
```

Full test suite passes including PostgreSQL integration tests. All stubs removed. Drift audit (`/zero-shot-sync`) returns VERIFIED.
