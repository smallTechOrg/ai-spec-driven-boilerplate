# Roadmap — DataChat

---

## What This Agent Does

DataChat is a private, single-user, browser-based agent for ad-hoc analysis of spreadsheet data. One person uploads CSV/Excel files into a persistent **library** they return to across days, picks a dataset, and holds a **multi-turn conversation** against it in plain language. Questions return prose answers with the key numbers, plus (in later phases) pivot/summary tables and interactive charts.

The defining property is **privacy via local code execution**: the agent never sends raw data rows to the LLM. It writes pandas analysis code that runs **locally** over the file; the LLM only ever sees the **question**, the dataset **schema/profile**, and the **computed results**. For non-trivial questions it runs a bounded plan → write-code → run-locally → inspect → iterate loop until it lands the answer.

## Who Uses It

A single analyst / power user working with their own spreadsheet exports on their own machine. They are comfortable with data but want to ask questions in natural language instead of writing pandas by hand. They value privacy (the raw rows must not leave the box), transparency (they want to see the code that produced the number), and continuity (the dataset and the conversation persist across days). No second user, no auth, no sharing.

## Core Problem Being Solved

Answering ad-hoc questions about a spreadsheet today means either writing pandas/SQL by hand or pasting data into a chatbot — the first is slow and repetitive, the second leaks the raw data to a third party and hallucinates numbers it cannot actually compute. DataChat removes both problems: natural-language questions, real computed answers, and the raw rows never leave the local machine.

## Success Criteria

- [ ] A user can upload a CSV up to ~100MB and get an auto-generated profile (columns, dtypes, ranges, row count) without the raw rows ever being sent to the LLM.
- [ ] A natural-language question returns a prose answer whose key numbers are computed by locally-executed pandas code, with the exact code shown to the user, in under 30s on the tested path.
- [ ] The LLM request payload provably contains only the question + schema/profile + prior computed results — never raw data rows (asserted in tests by inspecting the outbound prompt).
- [ ] The library, the conversation history, and the full run history (every question, the code that ran, the result, tokens, cost, timestamps) persist across server restarts.
- [ ] For an ambiguous or failing question the agent self-corrects on code errors (bounded retries) and, when still uncertain, flags assumptions / asks a clarifying question rather than inventing a confident wrong answer.

## What This Agent Does NOT Do (Out of Scope)

- No multi-user, no auth, no sharing, no cloud deployment — single local user only.
- No raw data rows are ever sent to the LLM, under any feature.
- No write-back to source files; datasets are read-only once uploaded.
- No external integrations (no databases, warehouses, BI tools, Slack, email).
- No model fine-tuning or learned ranking; behaviour is prompt-driven and deterministic-where-possible.
- No arbitrary shell / network access from generated code — execution is sandboxed to pandas over the loaded dataframe(s).
- No scheduled / automated runs — every analysis is user-triggered from the browser.

## Key Constraints

- **Privacy spine (hard):** the LLM payload may contain only question + schema/profile + computed results. Enforced in code and asserted in tests.
- **File size:** datasets up to ~100MB; **latency target:** sub-30s per answer on the tested path.
- **Stack is fixed** (see [architecture.md `## Stack`](architecture.md#stack)): Python, FastAPI + LangGraph + pandas, SQLite (production driver — tests run on SQLite too), **Gemini** as the LLM provider (`AGENT_GEMINI_API_KEY`), Next.js static export served single-origin under FastAPI at `/app/` on port 8001.
- **Sandboxed execution:** generated code runs in a restricted namespace with no filesystem/network builtins beyond the supplied dataframe and a whitelisted import set.
- **Bounded loop:** the iterate loop has a hard step cap so a confused agent terminates and degrades honestly rather than looping forever.

## Capabilities

| Capability | Summary | Introduced |
|-----------|---------|-----------|
| [dataset_library](capabilities/dataset_library.md) | Upload a CSV/Excel file, auto-profile it, persist it in a library the user returns to across days. | P1 (single file, single session) → P2 (persistent multi-day list) → P4 (multi-file join / folder-as-one) |
| [analyze_dataset](capabilities/analyze_dataset.md) | The privacy-preserving agentic loop: plan → write pandas code → run locally → inspect → iterate → prose answer. | P1 (single pass) → P3 (bounded plan-then-iterate + reflection + uncertainty) → P4 (tables + charts) |
| [conversation](capabilities/conversation.md) | Multi-turn chat against a dataset with turn memory; full run history persisted. | P2 |
| [run_observability](capabilities/run_observability.md) | Collapsible code panel, step timeline, per-question token + cost, daily total, answer streaming. | P1 (code panel + per-question cost, no stream) → P4 (live timeline, streaming, daily total) |

See [capabilities/index.md](capabilities/index.md).

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** Real backend on the one core path (upload → profile → ask → coded answer with code + cost), every other surface a clearly-labelled NON-FUNCTIONAL stub. The LangGraph skeleton (plan / generate-code / execute-local / finalize / error nodes + state + assembly) is wired in Phase 1 even though the deeper iterate loop is minimal. The privacy-preserving local-execution path is REAL in Phase 1 — no fake data on the tested path.

### Phase 1 — Upload, Profile, Ask (the privacy-preserving core path)

- **Goal:** Upload one CSV → the agent auto-profiles it (columns, dtypes, ranges, row count) → the user asks ONE natural-language question → the agent plans, writes pandas code, runs it LOCALLY (raw rows never leave the box), and returns a PROSE answer with the key numbers, SHOWING the exact code it ran and the token/cost for that question.
- **Independent slices (parallel build units):**
  - `db-migration` (backend) — new tables `datasets`, `dataset_profiles`, `analysis_runs` via a single Alembic revision; SQLAlchemy models. deps: none.
  - `analysis-engine` (backend) — LangGraph graph rework: `AgentState` for analysis, nodes `plan` / `generate_code` / `execute_local` / `finalize` / `handle_error`, the sandboxed local executor, the Gemini prompts (`src/prompts/plan.md`, `src/prompts/generate_code.md`), profiling service, token/cost accounting. deps: `db-migration` (reads/writes the new models). Serializes after `db-migration`.
  - `api-routes` (backend) — `POST /datasets` (upload+profile), `GET /datasets/{id}`, `POST /datasets/{id}/ask`, `GET /runs/{id}`; request/response domain models. deps: `analysis-engine`, `db-migration`.
  - `frontend` (frontend) — upload control + dataset/profile panel + single-question chat box + answer card with collapsible code panel + per-question token/cost; clearly-labelled non-functional stubs for library list, multi-file, charts, pivot tables, step timeline, follow-ups, data-quality flags, daily cost total, run-history browser, token streaming. deps: none (codes against the documented `api.md` contract; mock-free once `api-routes` lands).
- **Key surfaces / files:**
  - `db-migration`: `alembic/versions/0002_datachat.py`, `src/db/models.py`.
  - `analysis-engine`: `src/graph/state.py`, `src/graph/nodes.py`, `src/graph/edges.py`, `src/graph/agent.py`, `src/graph/runner.py`, `src/analysis/executor.py`, `src/analysis/profile.py`, `src/analysis/cost.py`, `src/prompts/plan.md`, `src/prompts/generate_code.md`, `src/config/settings.py` (add upload dir, model id, step cap).
  - `api-routes`: `src/api/datasets.py`, `src/api/runs.py`, `src/api/__init__.py` (router wiring), `src/domain/dataset.py`, `src/domain/analysis.py`.
  - `frontend`: `frontend/src/app/page.tsx`, `frontend/src/components/*` (new), `frontend/src/lib/api.ts`.
  - Tests: `tests/test_phase1_profile.py`, `tests/test_phase1_analyze.py`, `tests/test_phase1_privacy.py`, `tests/test_phase1_api.py`.
- **Gate command:** `uv run alembic upgrade head && uv run pytest` (real Gemini via `.env`, SQLite driver), plus boot check `uv run python -m src` and `cd frontend && pnpm build` producing a styled `/app/` page.
- **How the user tests it (handoff seed):** Run `uv run alembic upgrade head`, `cd frontend && pnpm build`, then `uv run python -m src`; open `http://localhost:8001/app/`. Upload a CSV (e.g. a sales export). Confirm the dataset panel shows the column list, dtypes, ranges, and row count. Type one question (e.g. "What is the total revenue by region?"). Confirm a prose answer with the numbers appears, expand the "Show code" panel to see the pandas code that ran, and see the token count + cost for that question. **Labelled stubs (not bugs):** the library list, multi-file/folder controls, chart/table toggles, the step timeline, follow-up suggestions, data-quality flags, the running daily-cost total, the run-history browser, and live token streaming are visible but greyed/badged "Coming soon".

### Phase 2 — Persistent Library + Multi-Turn Conversation

- **Goal:** The user's uploaded datasets persist across days in a real library list they can pick from; a question is part of a multi-turn conversation that remembers prior turns; every run is recorded in persisted run history.
- **Independent slices (parallel build units):**
  - `db-migration` (backend) — add `conversations`, `messages` tables; link `analysis_runs` to a conversation + message. deps: none.
  - `conversation-engine` (backend) — thread prior turns (question + computed-result summaries, never raw rows) into the `plan`/`generate_code` prompts; conversation + history services. deps: `db-migration`.
  - `library-api` (backend) — `GET /datasets` (list), `DELETE /datasets/{id}`, `GET /conversations`, `GET /conversations/{id}`, `POST /conversations` (`{dataset_id}`), `GET /conversations/{id}/messages`, history under `GET /runs?conversation_id=`. deps: `db-migration`, `conversation-engine`.
  - `frontend` (frontend) — wire the library list and conversation thread to real endpoints; persist the selected dataset/conversation; render the multi-turn transcript. deps: `library-api` (contract in `api.md`).
- **Key surfaces / files:** backend: `alembic/versions/0003_conversations.py`, `src/db/models.py`, `src/analysis/conversation.py`, `src/graph/nodes.py` (prompt threading), `src/api/datasets.py`, `src/api/conversations.py`, `src/api/runs.py`; frontend: `frontend/src/components/Library.tsx`, `frontend/src/components/Conversation.tsx`, `frontend/src/lib/api.ts`. Tests: `tests/test_phase2_library.py`, `tests/test_phase2_conversation.py`.
- **Gate command:** `uv run pytest` (real Gemini via `.env`, SQLite driver).
- **How the user tests it (handoff seed):** Restart the server; confirm previously-uploaded datasets still appear in the library list and are selectable. Open a dataset, ask a question, then ask a follow-up that depends on the prior turn (e.g. "now break that down by month") and confirm the answer uses the prior context. Confirm the conversation transcript shows all turns and survives a page reload. **Labelled stubs (not bugs):** charts/pivot tables, the live step timeline, follow-up suggestions, data-quality flags, the daily-cost total, the run-history browser UI, token streaming, multi-file/folder.

### Phase 3 — Reasoning Loop: Plan-Then-Iterate, Reflection, Uncertainty, Proactivity

- **Goal:** For non-trivial or failing questions the agent runs a real bounded plan → code → run → inspect → iterate loop with self-correction on code errors; it flags data-quality issues at profile time, suggests 2–3 follow-up questions after each answer, and handles uncertainty honestly (clarifying question / shown attempts / flagged best-guess).
- **Independent slices (parallel build units):**
  - `reasoning-loop` (backend) — promote the graph: add `inspect` (reflect on result/error) node, conditional iterate edge with a hard step cap, retry-on-code-error (reflection pattern), uncertainty handling (assumptions / clarifying question / flagged best-guess) in `finalize`. deps: none (extends existing nodes/edges).
  - `data-quality` (backend) — profile-time flags (nulls, dupes, outliers) added to `dataset_profiles`; surfaced via the profile API. deps: none.
  - `followups` (backend) — generate 2–3 suggested follow-up questions in `finalize` from question + result summary; expose on the ask/answer response. deps: none.
  - `frontend` (frontend) — wire the step timeline (planning → running code → checking result) from run steps, data-quality flag chips, and clickable follow-up suggestions. deps: backend slices' contracts in `api.md`.
- **Key surfaces / files:** backend: `src/graph/nodes.py`, `src/graph/edges.py`, `src/graph/agent.py`, `src/graph/state.py` (`step`, `max_steps`, `attempts`, `assumptions`, `followups`), `src/analysis/profile.py` (quality flags), `src/prompts/inspect.md`, `src/prompts/followups.md`, `src/db/models.py` + `alembic/versions/0004_run_steps.py` (`run_steps` table); frontend: `frontend/src/components/StepTimeline.tsx`, `frontend/src/components/Followups.tsx`, `frontend/src/components/QualityFlags.tsx`. Tests: `tests/test_phase3_loop.py`, `tests/test_phase3_quality.py`, `tests/test_phase3_followups.py`.
- **Gate command:** `uv run pytest` (real Gemini via `.env`, SQLite driver). The loop test uses a question whose first generated code deliberately/likely errors (e.g. references a column requiring a cleaning step) so the iterate + reflection path is exercised, not just the happy path.
- **How the user tests it (handoff seed):** Ask a question that needs a couple of steps (e.g. "which product had the biggest month-over-month drop?"). Watch the step timeline populate (planning → running code → checking result), expand each step's code. Ask something ambiguous (e.g. "best customer?") and confirm the agent either asks a clarifying question or states its assumption explicitly. Confirm the profile panel shows data-quality flags and that 2–3 follow-up suggestions appear under each answer and are clickable. **Labelled stubs (not bugs):** charts/pivot table rendering, the running daily-cost total, the run-history browser UI, token streaming, multi-file/folder.

### Phase 4 — Rich Output + Live Observability + Multi-File

- **Goal:** Answers can include interactive charts and pivot/summary tables; the answer streams token-by-token with the step timeline updating live; the running daily-cost total and the full run-history browser are real; the user can analyze several similarly-shaped files together (join / folder-as-one).
- **Independent slices (parallel build units):**
  - `viz-engine` (backend) — generated code may emit a typed chart/table spec (Vega-Lite-style spec for charts, records for tables) alongside the prose; chart/table spec validated and returned. deps: none.
  - `streaming-api` (backend) — Server-Sent-Events endpoint `GET /conversations/{id}/ask/stream` emitting step events + answer tokens; daily-cost aggregate `GET /usage/daily`; run-history list `GET /runs`. deps: none.
  - `multifile` (backend) — multiple datasets / a folder of similarly-shaped exports loaded as one logical dataset (concatenate / join) in the executor and profiler. deps: none (additive to executor).
  - `frontend` (frontend) — render charts (chart lib) + pivot tables, consume the SSE stream for live timeline + token streaming, show the daily-cost total and a run-history browser, multi-file/folder picker. deps: backend slices' contracts in `api.md`.
- **Key surfaces / files:** backend: `src/analysis/viz.py`, `src/analysis/executor.py` (multi-frame), `src/analysis/profile.py` (multi-file profile), `src/api/conversations.py` (SSE), `src/api/usage.py`, `src/api/runs.py`, `src/prompts/generate_code.md` (chart/table spec), `alembic/versions/0005_multifile.py`; frontend: `frontend/src/components/Chart.tsx`, `frontend/src/components/PivotTable.tsx`, `frontend/src/components/RunHistory.tsx`, `frontend/src/components/DailyCost.tsx`, `frontend/src/components/MultiFilePicker.tsx`, `frontend/src/lib/sse.ts`. Tests: `tests/test_phase4_viz.py`, `tests/test_phase4_stream.py`, `tests/test_phase4_multifile.py`.
- **Gate command:** `uv run pytest` (real Gemini via `.env`, SQLite driver). The multi-file test loads a dataset large enough (two files / >100k combined rows) that a sampled answer and a full-data answer differ, proving the executor runs over the full combined data, not a sample.
- **How the user tests it (handoff seed):** Ask for a breakdown that warrants a chart (e.g. "plot monthly revenue") and confirm an interactive chart renders; ask for a pivot (e.g. "revenue by region by quarter") and confirm a pivot table renders. Watch the answer stream token-by-token with the timeline updating live. Confirm the daily-cost total increments across questions and the run-history browser lists past runs with their code/result/tokens/cost/timestamps. Select two similarly-shaped files (or a folder) and confirm a question answers over the combined data. **No stubs remain** — every capability is real.
