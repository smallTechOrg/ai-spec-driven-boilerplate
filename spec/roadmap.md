# Roadmap

## What This Agent Does

The Data Analysis Agent is a single-origin web app: a user uploads a tabular data file (CSV
to start) and asks a natural-language question about it. The agent analyses the **real**
uploaded data and answers with three things, every time:

1. **Concrete real numbers** — computed from the actual rows in the file, not estimated or
   hallucinated.
2. **A short plain-language explanation** of what those numbers mean.
3. **The actual code/computation it ran** — the exact pandas/Python the agent executed,
   returned in the response and rendered in the UI, so every answer is auditable.

The agent is built around two hard product guarantees:

- **Data stays local.** The uploaded file and any derived dataframe live only on the local
  machine. Only the table **schema + a small sample/summary** are sent to the LLM so it can
  decide *what computation to run*. The full raw dataset never leaves the box. The LLM
  proposes code; a **local sandboxed Python/pandas step** runs that code over the full local
  dataframe.
- **Show its work.** The exact code the agent ran is captured alongside its result and
  returned to the user — answer, explanation, and code, together, on every query.

## Who Uses It

A data-literate but non-engineer knowledge worker — an analyst, operations lead, product
manager, or researcher — who has a spreadsheet and a question, wants a trustworthy numeric
answer fast, and needs to **see and verify the computation** rather than trust a black box.
Secondary user: an engineer who wants a quick, auditable first-pass analysis without opening
a notebook.

## Core Problem Being Solved

Today this person either (a) writes pandas/SQL by hand (slow, requires skill), or (b) pastes
data into a generic LLM chat — which is both a **data-leak risk** (the whole dataset leaves
their machine) and a **trust risk** (the model may invent numbers with no shown computation).
This agent removes both: the raw data never leaves the machine, and every answer ships with
the real numbers *and* the exact code that produced them.

## Success Criteria

- [ ] A user can upload a CSV and ask a natural-language question and receive a response
      containing all three of: numeric answer, plain-language explanation, and the executed
      code — in a single round trip.
- [ ] The numeric answer matches a hand-computed result over the same file for the gate's
      benchmark questions (aggregation, group-by, filter, correlation, messy-column) within
      floating-point tolerance.
- [ ] Only schema + a bounded sample/summary (never the full dataset) is sent to the LLM —
      verifiable from the captured LLM request and the observability log.
- [ ] The executed code returned to the user, when re-run against the same uploaded file,
      reproduces the same numeric result.
- [ ] A bad CSV, an empty/irrelevant question, or LLM-proposed code that errors produces a
      clear human-readable error in the UI (never a stack trace, never a crash).

## What This Agent Does NOT Do (Out of Scope)

- **No multi-file / joins** in v1 — one uploaded file per query (multi-file is a labelled
  stub, wired in a later phase).
- **No charts / visualizations** in v1 — numeric + text + code only (charts are a labelled
  stub).
- **No Excel-specific handling** in v1 — CSV only on the working path (`.xlsx` is a labelled
  stub).
- **No multi-turn chat memory** in v1 — each question is independent, single-turn
  (conversation memory is a labelled stub).
- **No external database connections** in v1 — uploaded files only (DB connectors are a
  labelled stub).
- **No data egress** — the full raw dataset is never sent to the LLM or any third party, by
  design, in every phase.
- **No write-back / data mutation** — the agent reads and computes; it never modifies or
  exports the user's source data.
- **No auth / multi-tenant accounts** — single-origin local tool; no login.

## Key Constraints

- **Data locality (hard):** full dataset stays on the local box; only schema + bounded sample
  reaches the LLM. See `spec/agent.md`.
- **Auditability (hard):** executed code is captured and returned on every query.
- **Sandboxed execution:** LLM-proposed code runs in a restricted local Python environment
  with a wall-clock timeout and a constrained namespace (see `spec/architecture.md` →
  *Local code sandbox*).
- **Production DB driver is SQLite** (`sqlite:///./data/agent.db`) for this project — gate
  tests run against SQLite because **SQLite IS the production driver here** (not PostgreSQL).
- **LLM provider is Gemini** (`gemini-2.5-flash` default), auto-detected from
  `AGENT_GEMINI_API_KEY`. Per-run budget caps from settings apply.
- **Upload size cap:** CSV files up to 50 MB / 1,000,000 rows on the working path (see
  `Assumed` lines in `spec/architecture.md`).

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** Its backend is minimal but
> REAL on the one core path (upload one CSV → ask one question → get answer + explanation +
> real executed code). Its frontend is visually complete: the real upload + question + answer
> UI, PLUS clearly-labelled NON-FUNCTIONAL stubs for everything coming later (multi-file,
> charts, Excel, chat memory, DB connections). Each later phase wires a stub into real
> functionality, one user-testable increment at a time.

### Phase 1 — Upload one CSV, ask one question, get an audited answer

- **Goal:** A user opens the live web app, uploads ONE CSV, types ONE natural-language
  question, and gets back a single response with (a) the real numeric answer computed from
  the real data, (b) a short plain-language explanation, and (c) the exact pandas code the
  agent ran. Single file, single-turn, real local analysis. Nothing more.

- **Independent slices (parallel build units):**
  - `db-schema` (backend) — adds the `DatasetRow` and `QueryRow` tables + the Alembic
    migration. Deps: none. (Other backend slices import these models but do not need the
    migration *applied* to be authored; the gate applies it.)
  - `csv-ingest` (backend) — local file load + schema/sample/summary derivation utility
    (`src/tools/dataset.py`). Deps: none (pure local pandas; no LLM, no DB).
  - `sandbox-exec` (backend) — the local sandboxed pandas-code execution step
    (`src/tools/sandbox.py`). Deps: none (pure local; takes a dataframe + code string,
    returns result/error).
  - `analysis-graph` (backend) — replaces the `transform_text` capability slot with the
    CSV-analysis nodes/edges/state/prompt and wires the runner. Deps: `csv-ingest`,
    `sandbox-exec` (imports their functions), and `db-schema` (persists `QueryRow`).
    **Serializes after those three.**
  - `analysis-api` (backend) — the `/datasets` (upload) and `/datasets/{id}/ask` endpoints +
    domain models. Deps: `analysis-graph` (calls the runner) and `db-schema`. **Serializes
    after `analysis-graph`.**
  - `analysis-ui` (frontend) — replaces `page.tsx`: real upload control + question box +
    answer panel (numbers, explanation, code block), PLUS labelled non-functional stubs.
    Deps: none — builds in parallel against the API contract in `spec/api.md` (mock-free; it
    calls the real endpoints once they land, but its code does not import backend code).

  Fan-out: `db-schema`, `csv-ingest`, `sandbox-exec`, and `analysis-ui` run **concurrently**
  (disjoint paths). `analysis-graph` runs after its three deps; `analysis-api` runs after
  `analysis-graph`.

- **Key surfaces / files:**
  - `db-schema`: `src/db/models.py` (add `DatasetRow`, `QueryRow`), `alembic/versions/*`
  - `csv-ingest`: `src/tools/dataset.py`
  - `sandbox-exec`: `src/tools/sandbox.py`
  - `analysis-graph`: `src/graph/nodes.py` (replace `transform_text` slot),
    `src/graph/state.py`, `src/graph/edges.py`, `src/graph/agent.py`, `src/graph/runner.py`,
    `src/prompts/transform.md` (replace with the analysis prompt)
  - `analysis-api`: `src/api/datasets.py`, `src/api/__init__.py` (register router),
    `src/domain/run.py` (or new `src/domain/analysis.py`)
  - `analysis-ui`: `frontend/src/app/page.tsx`
  - Tests (each slice owns its own): `tests/unit/test_dataset.py`,
    `tests/unit/test_sandbox.py`, `tests/integration/test_analysis_graph.py`,
    `tests/integration/test_analysis_api.py`

- **Gate command:**
  `uv run alembic upgrade head && uv run pytest tests/unit/test_dataset.py tests/unit/test_sandbox.py tests/integration/test_analysis_graph.py tests/integration/test_analysis_api.py -q`
  — run against the **real Gemini key from `.env`** (`AGENT_GEMINI_API_KEY`) and the **real
  SQLite production DB** (`sqlite:///./data/agent.db`). The integration tests upload a real
  CSV fixture and assert the numeric answer, the presence of executed code, and that re-running
  the captured code reproduces the number. Then live-server smoke:
  `uv run python -m src` → `curl http://localhost:8001/health` returns 200 and
  `curl http://localhost:8001/app/` serves the styled page.

- **How the user tests it (handoff seed):**
  1. Build the frontend: `cd frontend && pnpm install && pnpm build` (produces `frontend/out`).
  2. Start the app: `uv run python -m src` (serves API + UI single-origin on port 8001).
  3. Open `http://localhost:8001/app/` in a browser.
  4. Click the upload control and choose the provided sample CSV
     (`tests/fixtures/sales.csv` — a small sales table with `region`, `amount`, `date`,
     `units` columns).
  5. In the question box type: **"What is the total amount, and which region has the highest
     average amount?"** and click **Analyze**.
  6. Expect, within a few seconds: a numeric **Answer** (a total figure + the named region),
     a short **Explanation** paragraph, and a **Code** block showing the pandas the agent ran
     (e.g. a `groupby('region')['amount'].mean()` and a `['amount'].sum()`).
  7. **Labelled stubs (real, visible, intentionally inert — NOT bugs):** a greyed-out
     "Add another file" multi-file control, a "Charts (coming soon)" panel, an ".xlsx
     (coming soon)" badge near upload, a disabled "Continue the conversation" follow-up box,
     and a "Connect a database (coming soon)" button. Each is labelled "Coming soon" so it is
     never mistaken for a broken feature.

- **Cross-cutting Definition of Done (every slice):** README delta (applied serially after
  the parallel slices land) · a structured log line per new operation (csv load, LLM
  code-proposal call, sandbox execution, LLM explanation call, DB write, each new API
  endpoint, each new graph node) · error handling + timeout on each new external/sandbox call
  (bad CSV, sandbox timeout/exception, LLM failure → human-readable error, no crash) · a real
  behaviour-asserting test (asserts the actual number + presence of code, against the real
  Gemini key + real SQLite) · an incremental drift check — see
  `harness/patterns/phases.md` Horizontal Axis.

### Phase 2 — Multi-turn analysis on the same file (wire the chat-memory stub)

- **Goal:** Wire the "Continue the conversation" stub into real functionality: a user can ask
  a follow-up question about the **same uploaded dataset** and the agent uses prior turns as
  context (e.g. "now break that down by month"). Single file still; conversation memory keyed
  by dataset.

- **Independent slices (parallel build units):**
  - `memory-graph` (backend) — wire the existing `load_memory`/`write_memory` seam nodes into
    the analysis path, scoped by `dataset_id` as the conversation key; pass prior turns into
    the code-proposal prompt. Deps: none beyond Phase 1 (edits graph + nodes only).
  - `ask-api-memory` (backend) — accept/return a `conversation_id` (= `dataset_id`) on the
    `/ask` endpoint and persist turns via the existing `turns` table. Deps: `memory-graph`.
  - `chat-ui` (frontend) — turn the labelled follow-up stub into a real running Q&A thread on
    the dataset page. Deps: none (parallel, against the updated `spec/api.md`).

- **Key surfaces / files:** `src/graph/nodes.py`, `src/graph/edges.py`, `src/api/datasets.py`,
  `frontend/src/app/page.tsx`; tests `tests/integration/test_followup.py`.
- **Gate command:**
  `uv run alembic upgrade head && uv run pytest tests/integration/test_followup.py -q`
  (real Gemini key from `.env` + real SQLite). The test asks an initial question then a
  pronoun/anaphoric follow-up and asserts the second answer's numbers reflect the prior turn.
- **How the user tests it (handoff seed):** Rebuild frontend, restart `uv run python -m src`,
  open `/app/`, upload `tests/fixtures/sales.csv`, ask the Phase-1 question, then in the
  now-active follow-up box ask **"Now show that same average broken down by month"** and see
  a fresh answer + explanation + code that builds on the first. Remaining stubs (multi-file,
  charts, Excel, DB) stay labelled.
- **Cross-cutting Definition of Done (every slice):** README delta (applied serially after the
  parallel slices land) · a structured log line per new operation · error handling + timeout
  on each new external call · a real behaviour-asserting test · an incremental drift check —
  see `harness/patterns/phases.md` Horizontal Axis.

### Phase 3 — Excel (.xlsx) ingestion (wire the Excel stub)

- **Goal:** Wire the ".xlsx (coming soon)" stub into real functionality: a user can upload an
  Excel file (first/selected sheet) and ask questions exactly as with CSV. Same analysis loop;
  only the local load path changes.

- **Independent slices (parallel build units):**
  - `excel-ingest` (backend) — extend `src/tools/dataset.py` to load `.xlsx` (via openpyxl)
    into the same dataframe abstraction; add `openpyxl` to `[project.dependencies]`. Deps:
    none beyond Phase 1.
  - `upload-api-excel` (backend) — accept `.xlsx` content-type/extension on upload; record
    source format on `DatasetRow`. Deps: `excel-ingest`.
  - `upload-ui-excel` (frontend) — enable the Excel badge/upload, drop the "coming soon"
    label. Deps: none (parallel).

- **Key surfaces / files:** `src/tools/dataset.py`, `src/api/datasets.py`, `pyproject.toml`,
  `frontend/src/app/page.tsx`; tests `tests/unit/test_excel_ingest.py`,
  `tests/integration/test_excel_ask.py`.
- **Gate command:**
  `uv run pytest tests/unit/test_excel_ingest.py tests/integration/test_excel_ask.py -q`
  (real Gemini key from `.env` + real SQLite). Uploads a real `.xlsx` fixture and asserts the
  same numeric correctness as the CSV path.
- **How the user tests it (handoff seed):** Rebuild frontend, restart the app, open `/app/`,
  upload a provided `.xlsx` sample, ask a question, see answer + explanation + code. CSV path
  still works. Remaining stubs (multi-file, charts, DB) stay labelled.
- **Cross-cutting Definition of Done (every slice):** README delta (applied serially after the
  parallel slices land) · a structured log line per new operation · error handling + timeout
  on each new external call · a real behaviour-asserting test · an incremental drift check —
  see `harness/patterns/phases.md` Horizontal Axis.

### Phase 4 — Charts (wire the visualization stub)

- **Goal:** Wire the "Charts (coming soon)" panel into real functionality: when a question is
  naturally chartable (a group-by or time series), the agent additionally proposes a small,
  data-derived chart spec computed locally, and the UI renders it alongside the numeric answer.
  Numbers + explanation + code remain; the chart is additive.

- **Independent slices (parallel build units):**
  - `chart-graph` (backend) — extend the analysis loop so the LLM may propose a chart-data
    computation (returning a small aggregated table) and a chart type; the sandbox computes
    the chart data locally (still no raw data egress). Deps: none beyond Phase 1.
  - `chart-api` (backend) — include an optional `chart` object (type + aggregated series) in
    the `/ask` response. Deps: `chart-graph`.
  - `chart-ui` (frontend) — render the chart in the previously-stubbed panel (lightweight
    client charting lib). Deps: none (parallel).

- **Key surfaces / files:** `src/graph/nodes.py`, `src/tools/sandbox.py`, `src/api/datasets.py`,
  `src/domain/analysis.py`, `frontend/src/app/page.tsx`, `frontend/package.json`; tests
  `tests/integration/test_chart.py`.
- **Gate command:**
  `uv run pytest tests/integration/test_chart.py -q` (real Gemini key from `.env` + real
  SQLite). Asserts a chartable question yields a `chart` object whose aggregated series matches
  a locally hand-computed group-by.
- **How the user tests it (handoff seed):** Rebuild frontend, restart, open `/app/`, upload
  `tests/fixtures/sales.csv`, ask **"Show average amount by region"**, and see the answer +
  explanation + code AND a rendered bar chart of the per-region averages. Remaining stubs
  (multi-file, DB) stay labelled.
- **Cross-cutting Definition of Done (every slice):** README delta (applied serially after the
  parallel slices land) · a structured log line per new operation · error handling + timeout
  on each new external call · a real behaviour-asserting test · an incremental drift check —
  see `harness/patterns/phases.md` Horizontal Axis.

> Multi-file/joins and external DB connections remain explicitly out of scope for the current
> roadmap (see *Out of Scope*); they stay labelled stubs and would each be added as a future
> phase only when required.
