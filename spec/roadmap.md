# Roadmap

Local Data Analyst — a personal, local-first data analysis agent for one power user.

---

## What This Agent Does

The Local Data Analyst is a personal, local-first agent that lets a single power user ask questions of their own spreadsheets in plain English and get a trustworthy, richly-formatted answer in seconds. The user uploads a CSV or Excel file (each Excel sheet is treated as its own dataset), the agent auto-profiles it, and then — for every question — it drafts a multi-step plan, generates and runs SQL against the data **locally** via DuckDB, and uses an LLM only to interpret schema and summary numbers into a plain-language answer with key-stat callouts, an auto-selected chart, a summary table, and a written insight. The defining property is the **privacy boundary**: raw data rows never leave the machine — only column metadata and aggregate/summary results are ever sent to the LLM.

## Who Uses It

A single technical power user (data analyst, founder, operator, or engineer) who works with their own spreadsheets every day. They are comfortable with data concepts but want to skip the manual cycle of writing pivot tables, charts, and SQL by hand. They will **act on the answers**, so correctness, transparency (they can inspect the exact query that ran), and privacy (sensitive rows stay local) matter more than breadth of features. The tool is single-user and runs as a long-running local service on their own machine.

## Core Problem Being Solved

Answering an ad-hoc question about a spreadsheet today means manually loading it, writing formulas or SQL, building a chart, and writing up the takeaway — repeated dozens of times a day, and lost the moment you close the file. Cloud "chat with your data" tools solve the manual labour but require uploading raw rows to a third party, which is a non-starter for sensitive data. This agent removes the manual labour **and** keeps every raw row on the user's machine, while showing exactly what it did so the user can trust the answer enough to act on it.

## Success Criteria

- [ ] A user can upload one CSV or Excel file (up to ~100 MB) and see an auto-generated data profile (row count, column names, types, null counts, basic stats) without writing any code.
- [ ] For a plain-English question over a loaded dataset, the agent returns a complete rich answer (plain-language answer + key-stat callouts + auto-selected chart + summary table + written insight) in under ~30 seconds end-to-end on the local machine.
- [ ] **Privacy boundary is verifiable:** an automated test asserts that no raw data-row value ever appears in any prompt sent to the LLM — only schema (column names/types) and aggregate/summary numbers cross to Gemini.
- [ ] Every query is persisted to an audit history (question, plan, generated SQL, result summary, token counts, estimated USD cost, timestamps) and is retrievable.
- [ ] The user can expand any answer to inspect the exact DuckDB SQL that ran, the plan steps, and the dataset profile, and can see the token count and estimated USD cost for that query.

## What This Agent Does NOT Do (Out of Scope)

- No multi-user accounts, authentication, sharing, or collaboration — it is single-user and local.
- No external integrations (databases, warehouses, SaaS APIs, cloud storage) — it reads local CSV/Excel files only.
- No sending of raw data rows to any LLM or remote service, ever — only schema + aggregates.
- No writing back to or mutating the user's source files — reads are non-destructive.
- No data formats other than CSV and Excel (`.xlsx`) in any phase; no PDF, JSON, Parquet, or images.
- No fine-tuning, training, or model hosting — it calls the hosted Gemini API for narration only.
- No deployment to the cloud — it is a local long-running service started by the user.
- No free-form data editing / spreadsheet-style cell editing — it answers questions, it is not an editor.

## Key Constraints

- **Privacy boundary (non-negotiable):** the LLM (Gemini) receives ONLY schema (column names/types) and aggregate/summary results. Raw data rows never leave the machine. DuckDB SQL runs locally; only column metadata + summarized numbers are sent to Gemini. This must be enforced in code AND asserted by a test/eval.
- **File size:** must handle files up to ~100 MB without loading the full file into the LLM (DuckDB streams/queries from disk).
- **Latency:** a typical question returns a full rich answer in under ~30 seconds on the local machine.
- **Reliability bar:** the user will act on the answers, so the agent must always show what it tried (plan + generated SQL) and flag uncertainty rather than silently guessing.
- **Local-only:** runs as a long-running local service (`uv run python -m src`), no external integrations, all data on-disk on the user's machine.
- **Cost:** default to the low-cost `gemini-2.5-flash` model; per-query token and estimated USD cost are captured and shown.

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** Its backend is minimal but REAL on the one core path (no fake data on the tested path). Its frontend is visually complete: real UI for the one working path PLUS clearly-labelled NON-FUNCTIONAL stubs for everything coming later. Each later phase wires those stubs into real functionality, one increment at a time. All vision requirements are covered by ~Phase 5.

The PLAN-THEN-EXECUTE LangGraph skeleton and the privacy boundary are **real in Phase 1** — later phases add nodes/features around that spine, they do not rebuild it. Slices are independent (parallel build units) unless a dependency is declared; the only Phase 1 dependency is **frontend → API contract**, which is fully specified in [api.md](api.md) so both slices build to the contract in parallel.

### Phase 1 — Ask one file (the core loop)

- **Goal:** Upload ONE CSV/Excel file → it auto-profiles → the user asks a question in plain English → the agent plans, runs DuckDB **locally** (only schema + aggregates to Gemini), and returns a rich answer (plain-language answer + key-stat callouts + auto-picked chart + summary table + written insight) with an expandable code/steps/profile panel, per-query token & cost, and the run saved to audit history. A small sample CSV ships so the path is testable immediately.
- **Independent slices (parallel build units):**
  - `backend-core` (backend) — ingestion (CSV/Excel parse → DuckDB), auto-profiler, the full PLAN-THEN-EXECUTE LangGraph (plan → local-execute → aggregate → narrate → suggest-follow-ups → finalize/handle_error), DuckDB query tool, Gemini flash wiring + token/cost capture, the privacy boundary + its test, SQLite models (Dataset, Run, Message) + Alembic migration, REST endpoints (`/api/datasets` upload, `/api/ask`, `/api/runs`, `/api/runs/{id}`), the sample CSV, and all backend tests. **Deps: none.**
  - `frontend-workspace` (frontend) — the single-page workspace: drag-drop/upload area, dataset profile card, question box, rich-answer render (answer + key-stat callouts + chart + summary table + insight), expandable code/steps/profile panel, per-query token+cost, follow-up chips (display-only in P1), and all LABELLED non-functional stubs (library sidebar, watched folder, multi-file join, session restore, daily-cost total, reproducible re-run). **Deps: API contract in [api.md](api.md) (build to the contract, no runtime dep at build time).**
- **Key surfaces / files (disjoint per slice):**
  - `backend-core` writes: `src/graph/state.py`, `src/graph/nodes.py`, `src/graph/agent.py`, `src/graph/edges.py`, `src/graph/runner.py`, `src/prompts/plan.md`, `src/prompts/narrate.md`, `src/prompts/follow_ups.md` (replaces `src/prompts/transform.md`), `src/domain/dataset.py`, `src/domain/ask.py`, `src/data/ingest.py`, `src/data/profiler.py`, `src/data/duckdb_engine.py`, `src/data/cost.py`, `src/db/models.py`, `src/api/datasets.py`, `src/api/ask.py`, `src/api/runs.py`, `src/api/__init__.py`, `alembic/versions/0002_data_analyst.py`, `samples/sample_sales.csv`, `tests/unit/...`, `tests/integration/...`.
  - `frontend-workspace` writes: `frontend/src/app/page.tsx`, `frontend/src/components/*.tsx`, `frontend/src/lib/api.ts`, `frontend/src/app/globals.css`, `frontend/package.json` (adds chart lib).
  - The two slices never touch the same file. `src/api/__init__.py` is owned by `backend-core` only.
- **Gate command:** `uv run alembic upgrade head && uv run pytest tests/ -q` (runs against real Gemini via `.env` and the production SQLite driver; the privacy-boundary test and the full ingest→profile→ask→narrate pipeline test are included). Frontend build check: `cd frontend && pnpm build` (produces `frontend/out/`).
- **How the user tests it (handoff seed):**
  1. Run `uv run alembic upgrade head` then `cd frontend && pnpm build && cd ..` then `uv run python -m src`.
  2. Open `http://localhost:8001/app/`.
  3. Drag the shipped `samples/sample_sales.csv` onto the upload area (or use the file picker). A profile card appears: row count, columns + types, null counts, basic stats. **(real)**
  4. Type a question such as "What were total sales by region?" and submit. Within ~30s a rich answer appears: plain-language answer, key-stat callouts, an auto-picked chart, a summary table, and a written insight. **(real)**
  5. Expand the "Code / Steps / Profile" panel to see the exact DuckDB SQL, the plan steps, and the profile. See the per-query token count + estimated USD. **(real)**
  6. The following are visible but clearly LABELLED as "Coming soon" stubs and must not be mistaken for bugs: library sidebar, watched folder, multi-file join, cross-day session restore, daily-cost total, reproducible re-run button. Follow-up suggestion chips are shown but display-only in Phase 1 **(labelled).**

### Phase 2 — Library & cross-day memory

- **Goal:** Loaded datasets persist in a library and the conversation/run history restores across days, so the user resumes where they left off — "load once, ask many."
- **Independent slices (parallel build units):**
  - `backend-library` (backend) — persist uploaded DuckDB datasets on disk per dataset, list/select/delete library entries, Session entity + restore-on-boot, conversation-history (Message) threading into the graph context. **Deps: none (extends Phase 1 models).**
  - `frontend-library` (frontend) — wire the (P1-stubbed) library sidebar to real list/select/delete; render restored conversation history and the previously-loaded dataset on load. **Deps: API contract for library + session endpoints (in [api.md](api.md)).**
- **Key surfaces / files:** backend → `src/data/library.py`, `src/api/datasets.py` (list/delete), `src/api/sessions.py`, `src/db/models.py` (Session), `alembic/versions/0003_*.py`, tests. frontend → `frontend/src/components/LibrarySidebar.tsx`, `frontend/src/components/HistoryPanel.tsx`, `frontend/src/lib/api.ts`.
- **Gate command:** `uv run alembic upgrade head && uv run pytest tests/integration/test_library_restore.py tests/unit/test_sessions.py -q` (real driver; asserts a dataset + conversation survive a process restart and are re-listed).
- **How the user tests it:** Upload two files, ask a question on each, stop the server (`Ctrl-C`), restart with `uv run python -m src`, reopen `http://localhost:8001/app/` — both datasets appear in the now-real library sidebar and prior Q&A history is restored. Watched folder / multi-file / daily-total remain labelled stubs.

### Phase 3 — Multi-file: join, compare, folder-as-dataset

- **Goal:** The user can join/compare two datasets and treat a folder of like-shaped files as one combined dataset; the agent picks the right file(s) for a question.
- **Independent slices (parallel build units):**
  - `backend-multifile` (backend) — DuckDB cross-dataset joins, folder-as-dataset ingestion (UNION of like-schema files), an auto-pick-file planning step in the graph. **Deps: none (extends Phase 1 graph + Phase 2 library).**
  - `frontend-multifile` (frontend) — wire the (stubbed) multi-file join + folder-as-dataset UI; show which file(s)/datasets a given answer used. **Deps: API contract for multi-dataset ask (in [api.md](api.md)).**
- **Key surfaces / files:** backend → `src/data/joins.py`, `src/data/folder_dataset.py`, `src/graph/nodes.py` (auto-pick step), `src/prompts/select_dataset.md`, tests. frontend → `frontend/src/components/DatasetPicker.tsx`, `frontend/src/components/JoinBuilder.tsx`, `frontend/src/lib/api.ts`.
- **Gate command:** `uv run alembic upgrade head && uv run pytest tests/integration/test_multifile.py -q` (real driver + real Gemini; asserts a join across two seeded datasets returns a correct aggregate and the privacy boundary still holds across both).
- **How the user tests it:** Upload two related files, ask a question that requires joining them ("average order value by customer segment"), and confirm the agent picks/joins the right datasets and answers correctly. Point a folder of like CSVs at the (now-real) folder-as-dataset control and ask across the whole folder. Watched folder remains a labelled stub.

### Phase 4 — Proactivity, clarification & ingestion ergonomics

- **Goal:** The agent becomes proactive and safe under ambiguity: clickable follow-up suggestions, a clarification gate that asks first when a question is ambiguous, and a watched local folder that auto-ingests dropped files.
- **Independent slices (parallel build units):**
  - `backend-proactive` (backend) — make follow-up suggestions clickable (round-trip), add a clarification-gate node (ask-first vs best-guess-with-flag), watched-folder ingestion service. **Deps: none (extends Phase 1 graph + Phase 2 library).**
  - `frontend-proactive` (frontend) — wire follow-up chips to re-ask, render the clarification prompt + uncertainty flags, wire the watched-folder control. **Deps: API contract for clarify + watch endpoints (in [api.md](api.md)).**
- **Key surfaces / files:** backend → `src/graph/nodes.py` (clarify node), `src/graph/edges.py` (clarify branch), `src/prompts/clarify.md`, `src/data/watcher.py`, `src/api/ask.py` (clarify round-trip), tests. frontend → `frontend/src/components/FollowUps.tsx`, `frontend/src/components/ClarifyPrompt.tsx`, `frontend/src/components/WatchedFolder.tsx`.
- **Gate command:** `uv run alembic upgrade head && uv run pytest tests/integration/test_clarify_and_watch.py -q` (real Gemini; asserts an ambiguous question triggers a clarification and a dropped file in the watched folder becomes a library dataset).
- **How the user tests it:** Ask a deliberately ambiguous question and confirm the agent asks a clarifying question (or gives a best guess with a visible uncertainty flag). Click a follow-up chip and confirm it re-asks. Drop a file into the configured watched folder and confirm it auto-appears in the library.

### Phase 5 — Cost rollup, derived tables & reproducible re-run

- **Goal:** Close out transparency/durability: a running daily-total cost rollup, user-named saved derived tables that persist, and a reproducible one-click re-run of any historical query from the audit log.
- **Independent slices (parallel build units):**
  - `backend-durability` (backend) — daily cost aggregation endpoint, save/persist derived tables (materialize a query result as a reusable DuckDB table + library entry), reproducible re-run (re-execute a stored Run's SQL). **Deps: none (extends Phase 1 audit + Phase 2 library).**
  - `frontend-durability` (frontend) — wire the (stubbed) daily-cost total, derived-table save/list UI, and the reproducible re-run button on history items. **Deps: API contract for cost + derived-table + rerun endpoints (in [api.md](api.md)).**
- **Key surfaces / files:** backend → `src/api/cost.py`, `src/data/derived.py`, `src/api/runs.py` (rerun), tests. frontend → `frontend/src/components/DailyCost.tsx`, `frontend/src/components/DerivedTables.tsx`, `frontend/src/components/RunHistory.tsx`.
- **Gate command:** `uv run alembic upgrade head && uv run pytest tests/integration/test_cost_derived_rerun.py -q` (real driver; asserts the daily total sums per-query costs, a saved derived table is queryable, and a re-run reproduces the original result).
- **How the user tests it:** Run several queries and confirm the daily-total cost matches the sum of per-query costs. Save a query result as a named derived table and ask a follow-up against it. Open the audit history and click "Re-run" on a past query — it reproduces the same answer. No labelled stubs remain.
