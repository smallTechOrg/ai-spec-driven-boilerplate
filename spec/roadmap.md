# Roadmap

## What This Agent Does

A browser-based chat interface where users upload a CSV file and ask natural-language questions about their data. The agent reads the CSV into an in-memory pandas DataFrame, sends the column schema and a sample of rows to Gemini, and returns a plain-English answer. In Phase 2 the agent also generates and sandboxed-executes pandas/matplotlib code to produce a chart (returned as a base64 PNG) alongside the executed code and agent reasoning trace.

## Who Uses It

Data analysts, business stakeholders, and technical users who have a CSV and want fast answers without writing code or configuring a BI tool. They upload once per session and ask many questions in a chat-style panel.

## Core Problem Being Solved

Users with CSV data spend time hand-writing pandas queries or wrangling pivot tables to answer ad-hoc questions. This agent removes that friction: one upload, then natural-language questions that return a text answer (and, in Phase 2, a chart plus the code that produced it).

## Success Criteria

- [ ] A user can upload any well-formed CSV and receive a `session_id` plus a column schema preview within 3 seconds.
- [ ] A natural-language question over the uploaded data returns a correct text answer within 15 seconds.
- [ ] The CSV data never leaves the server process — it is held in an in-memory dict keyed by `session_id` and is never written to disk.
- [ ] The backend returns a structured error (not a 500 crash) when the CSV is malformed or Gemini returns an unusable response.
- [ ] In Phase 2, a chart is returned as a base64 PNG alongside the executed Python code and a node trace for every successful answer.

## What This Agent Does NOT Do (Out of Scope)

- NL-to-SQL or any SQLite-backed data storage of CSV content.
- LangChain, LangSmith, or langchain-google-genai — the `google-genai` SDK is used directly.
- User authentication or per-user data isolation.
- Saving or persisting charts across sessions.
- Multi-file joins across more than one uploaded CSV.
- Writing back to the CSV or any data mutation.
- Ingesting data from cloud storage, S3, or URLs — only local file upload.
- Streaming token output from Gemini to the browser.

## Key Constraints

- CSV is held in-memory only: a `dict[session_id, pd.DataFrame]` on the server process. No disk write of CSV data.
- LLM provider: Google Gemini via the `google-genai` Python SDK (`google-genai>=2.9.0`). No LangChain.
- Model: `gemini-2.0-flash` (configurable via `AGENT_LLM_MODEL`).
- SQLite (`data/agent.db`) is used only for session and conversation metadata, not for CSV data.
- Dev port: 8001.
- Frontend: Next.js static export (`output: 'export'`, `basePath: '/app'`) served by FastAPI at `/app`; single-origin run path.

---

## Phases of Development

> Phase 1 is the smallest first-time-right user-testable win. Its backend is minimal but REAL on the one core path. Its frontend is visually complete: real UI for the working path PLUS clearly-labelled non-functional stubs for Phase 2 features.

---

### Phase 1 — CSV Upload + Text Answer (First Win)

**Goal:** A user uploads a CSV, asks one natural-language question, and receives a plain-English text answer — end-to-end against the real Gemini API. No charts yet. The UI shows the answer plus clearly-labelled stubs for the chart panel and code panel.

**Independent slices (parallel build units):**

- `slice-a` (backend) — all Python code: in-memory session store, 4-node LangGraph pipeline (`parse_csv` → `answer_question` → `handle_error` / `finalize`), sessions API router (`POST /sessions`, `POST /sessions/{session_id}/questions`, `GET /health`), DB models for session and run metadata, Alembic migration, system prompt, structlog observability, integration tests. **deps: none**

- `slice-b` (frontend) — all Next.js code: two-panel layout, CSV upload component (real), chat component (real), text answer display (real), chart panel stub (labelled), code panel stub (labelled). **deps: none**

**Key surfaces / files:**

`slice-a` owns (disjoint from frontend):
- `src/sessions/store.py` — in-memory DataFrame dict
- `src/graph/state.py` — extend AgentState
- `src/graph/nodes.py` — replace all nodes with: `parse_csv`, `answer_question`, `handle_error`, `finalize`
- `src/graph/edges.py` — conditional routing
- `src/graph/agent.py` — rewire graph
- `src/graph/runner.py` — extend runner
- `src/db/models.py` — extend/replace models (Session, ConversationRun)
- `src/api/sessions.py` — new router
- `src/api/__init__.py` — register new router
- `src/prompts/answer_question.md` — new system prompt
- `alembic/versions/` — new migration
- `tests/test_phase1.py` — integration tests
- `pyproject.toml` — add `pandas` if missing

`slice-b` owns (disjoint from backend):
- `frontend/src/app/page.tsx`
- `frontend/src/components/UploadPanel.tsx`
- `frontend/src/components/ChatPanel.tsx`
- `frontend/src/components/AnswerCard.tsx`
- `frontend/src/components/StubBadge.tsx`

**Gate command:**
```
uv run alembic upgrade head && uv run pytest tests/test_phase1.py -v --tb=short
```
Run from repo root. Requires `.env` with `AGENT_GEMINI_API_KEY`. Tests call the real Gemini API and write to the SQLite DB.

**How the user tests it (handoff seed):**
1. `cd frontend && pnpm install && pnpm build` — builds static export to `frontend/out/`
2. `uv run alembic upgrade head` — applies DB migration
3. `uv run python -m src` — starts FastAPI at `http://localhost:8001`
4. Open `http://localhost:8001/app/` (trailing slash required)
5. **Upload panel (REAL):** drag or pick any CSV file → click "Upload" → see session ID + column list appear below the button
6. **Chat panel (REAL):** type a question (e.g. "What is the average value in each column?") → click "Ask" → within ~15 s see a text answer appear in the chat thread
7. **Chart panel stub (LABELLED):** a greyed-out section labelled "Chart — Coming in Phase 2" appears below the text answer
8. **Code panel stub (LABELLED):** a greyed-out section labelled "Executed Code — Coming in Phase 2" appears below the chart stub

**Cross-cutting Definition of Done (every slice):**
- README updated with what this phase added (run commands, env vars required)
- A structured log line emitted per new operation (CSV parse, Gemini call, session create, run create)
- Error handling on each external call (Gemini API, file parse)
- At least one real behaviour-asserting test per new capability (shape + content assertions on real Gemini responses)
- Incremental drift check: code matches spec for every file the slice touches

---

### Phase 2 — Charts + Executed Code

**Goal:** Every answer now includes a matplotlib chart (returned as a base64 PNG) plus the Python code the agent executed to produce it, surfaced in the UI alongside the text answer.

**Independent slices (parallel build units):**

- `slice-a` (backend) — add two new graph nodes (`generate_code`, `execute_code`), extend `AgentState` with `chart_base64`, `executed_code`, `chart_type` fields, extend `ConversationRun` model with those columns, extend the `/sessions/{session_id}/questions` response to include `chart_base64`, `executed_code`, `chart_type`, add sandbox safety to the execute node, extend tests. **deps: none**

- `slice-b` (frontend) — wire the chart panel stub into a real `<img>` element rendering the base64 PNG, wire the code panel stub into a real syntax-highlighted code block, add `node_trace` collapsible section. **deps: none**

**Key surfaces / files:**

`slice-a` owns:
- `src/graph/nodes.py` — add `generate_code`, `execute_code` nodes
- `src/graph/state.py` — extend with `chart_base64`, `executed_code`, `chart_type`, `node_trace`
- `src/graph/agent.py` — rewire graph with new nodes
- `src/db/models.py` — add `chart_data` (JSON), `executed_code` columns
- `alembic/versions/` — new migration for new columns
- `src/prompts/generate_code.md` — new system prompt for code generation
- `tests/test_phase2.py` — integration tests

`slice-b` owns:
- `frontend/src/components/AnswerCard.tsx` — wire chart image + code block stubs into real panels
- `frontend/src/components/ChartPanel.tsx` — new component
- `frontend/src/components/CodePanel.tsx` — new component

**Gate command:**
```
uv run alembic upgrade head && uv run pytest tests/ -v --tb=short
```
Requires `.env` with `AGENT_GEMINI_API_KEY`. Tests call the real Gemini API and exercise the chart generation and code execution paths.

**How the user tests it (handoff seed):**
1. Build frontend and start backend as in Phase 1.
2. Upload a CSV, ask a question (e.g. "Show me a bar chart of total sales by region").
3. Within ~20 s: text answer appears, a real chart image (bar/line/scatter) renders below it, and the Python code the agent ran appears in a code block beneath the chart.
4. A collapsible "Reasoning trace" section shows which nodes ran and in what order.

**Cross-cutting Definition of Done (every slice):**
- README updated with Phase 2 additions
- Structured log line per new operation (code generation, code execution, chart render)
- Sandbox error handling — if executed code raises, `handle_error` is triggered and the user sees a readable message
- Real behaviour-asserting tests for chart generation and code execution paths
- Incremental drift check
