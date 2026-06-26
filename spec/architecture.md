# Architecture

## System Overview

The data-analysis agent is a single-origin web application: a FastAPI backend serves both the REST API and the pre-built Next.js static export from `frontend/out/`. There is no separate frontend server in production. The user's browser communicates exclusively with the FastAPI process on port 8001. CSV data never leaves the server process — it is held as a pandas DataFrame in a process-level in-memory dict keyed by `session_id`. It is never written to disk, never sent to any external service.

## Component Map

```
Browser
  │  GET /app/                    → FastAPI serves frontend/out/ (Next.js static export)
  │  POST /sessions               → FastAPI (CSV multipart → in-memory DataFrame)
  │  POST /sessions/{id}/questions → FastAPI → LangGraph pipeline → Gemini → response
  │  GET  /health                 → FastAPI liveness probe
  └──────────────────────────────────────────────────────────────────────────────────

FastAPI (src/)
  ├── api/sessions.py   POST /sessions, POST /sessions/{id}/questions
  ├── api/health.py     GET /health
  │
  ├── sessions/
  │   └── store.py      in-memory dict[session_id → pd.DataFrame]
  │
  ├── graph/            LangGraph pipeline (see spec/agent.md)
  │   ├── state.py      AgentState TypedDict
  │   ├── nodes.py      parse_csv, answer_question, handle_error, finalize
  │   │                 (Phase 2 adds: generate_code, execute_code)
  │   ├── edges.py      conditional routing (error → handle_error, else → next)
  │   ├── agent.py      graph assembly + compile()
  │   └── runner.py     run_question(session_id, question) → QuestionResult
  │
  ├── db/
  │   ├── models.py     Session, ConversationRun (SQLAlchemy ORM)
  │   └── session.py    SQLite engine + session factory
  │
  ├── config/settings.py  AGENT_* env vars (gemini_api_key, llm_model, etc.)
  ├── llm/
  │   ├── client.py       LLMClient wrapper (existing, used by answer_question node)
  │   └── providers/
  │       └── gemini.py   GeminiProvider using google-genai SDK
  ├── observability/    structlog configuration + get_logger()
  └── prompts/          system prompts (Markdown)

SQLite  data/agent.db
  ├── sessions          (metadata: session_id, filename, columns, row_count)
  └── conversation_runs (question history: run_id, session_id, question, answer, status)

In-memory (process lifetime)
  └── dict[session_id → pd.DataFrame]   CSV data, never written to disk
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API (`src/api/`) | Validate HTTP requests, invoke domain logic, serialize responses |
| Session store (`src/sessions/`) | In-memory dict mapping session_id to pandas DataFrame |
| Graph pipeline (`src/graph/`) | LangGraph pipeline — CSV parse, Gemini Q&A, error, finalize |
| LLM client (`src/llm/`) | `google-genai` SDK wrapper; GeminiProvider; per-call model override |
| Data (`src/db/`) | SQLAlchemy ORM for metadata tables only; no CSV data stored in DB |
| Config (`src/config/`) | `pydantic-settings` Settings class; all env vars with `AGENT_` prefix |
| Observability (`src/observability/`) | structlog JSON logs per operation |
| Frontend (`frontend/`) | Next.js static export; served by FastAPI at `/app` |

## Data Flow

1. **Upload:** User picks a CSV file in the browser → `POST /sessions` (multipart) → backend reads the file into a pandas DataFrame, stores it in `SESSION_STORE[session_id]`, writes a `Session` metadata row to SQLite → returns `{session_id, columns, row_count}` to browser. The CSV bytes are never written to disk.

2. **Question:** User types a question → `POST /sessions/{session_id}/questions {question}` → backend looks up `SESSION_STORE[session_id]` to get the DataFrame → calls `run_question(session_id, question, dataframe)`.

3. **Pipeline (Phase 1):** LangGraph executes two nodes in sequence:
   - `parse_csv`: validates the DataFrame from the session store, extracts `column_schema` (name + dtype for each column) and `sample_rows` (first 10 rows as a list of dicts).
   - `answer_question`: builds a prompt with the column schema + sample rows + user question, calls Gemini (`gemini-2.0-flash`) via the `google-genai` SDK, returns the text answer.

4. **Pipeline (Phase 2, additional nodes after `parse_csv`):**
   - `generate_code`: calls Gemini to produce a pandas/matplotlib Python code snippet that answers the question and generates a chart.
   - `execute_code`: runs the code in a sandboxed `exec()` environment with access only to the DataFrame and matplotlib; captures the matplotlib figure as a base64 PNG.

5. **Response:** Backend writes `ConversationRun` record, returns `{run_id, answer, chart_base64?, chart_type?, executed_code?, node_trace}`.

6. **Render:** Browser displays the text answer; in Phase 2 also renders the base64 PNG image and the executed code in a syntax-highlighted block.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Google Gemini API (`gemini-2.0-flash`) | Answer generation; Phase 2: code generation | Structured error returned; `ConversationRun.status = "failed"` written; user sees error message |
| SQLite (`data/agent.db`) | Session and run metadata storage | Startup fails loudly if `data/` directory is not writable |

## Stack

> This project's concrete technology choices. Generic rules live in `harness/patterns/tech-stack.md`; this section is only what this project picked.

- **Language:** Python 3.12+
- **Agent framework:** LangGraph `>=0.2` — sequential pipeline with a conditional error branch; see `spec/agent.md`
- **LLM provider + model:** Google Gemini via the `google-genai` Python SDK (`google-genai>=2.9.0`). Do NOT use `langchain-google-genai` or any LangChain package. Default model: `gemini-2.0-flash`. Configurable via `AGENT_LLM_MODEL`.
- **Backend:** FastAPI `>=0.115` + Uvicorn `[standard]>=0.30`. Dev port: **8001**.
- **Database + ORM:** SQLite (`data/agent.db`) + SQLAlchemy `>=2.0` (sync). Driver: built-in `pysqlite` — no extra package. Alembic `>=1.13` for schema migrations. SQLite stores only session and run metadata; CSV data is in-memory only.
- **Data analysis:** `pandas>=2.0` for DataFrame operations; `matplotlib>=3.8` for chart generation (Phase 2).
- **Frontend:** Next.js 15 + React 19, TypeScript, Tailwind v4. Static export (`output: 'export'`, `basePath: '/app'`). Served by FastAPI at `/app`. `postcss.config.mjs` required for Tailwind v4. `NODE_OPTIONS=--no-experimental-webstorage` in build/dev scripts.
- **Dependency management:** `uv` (Python / `pyproject.toml`) · `pnpm` (frontend / `package.json`)

| Key library | Version | Purpose |
|-------------|---------|---------|
| `google-genai` | `>=2.9.0` | Gemini API calls (direct SDK, no LangChain) |
| `langgraph` | `>=0.2` | Agent graph orchestration |
| `pandas` | `>=2.0` | In-memory CSV DataFrame operations |
| `matplotlib` | `>=3.8` | Chart generation to base64 PNG (Phase 2) |
| `python-multipart` | `>=0.0.9` | FastAPI file upload (multipart/form-data) |
| `structlog` | `>=24.1` | Structured JSON logging |
| `pydantic-settings` | `>=2.3` | Settings from env / `.env` with `extra="ignore"` |
| `alembic` | `>=1.13` | SQLite schema migrations for metadata tables |
| `httpx` | `>=0.27` | `TestClient` in tests |

**Avoid:**
- `langchain-google-genai`, `langchain`, `langsmith`, or any LangChain package — use `google-genai` SDK directly.
- Writing CSV data to disk — it must stay in the in-memory `SESSION_STORE` dict only.
- PostgreSQL or any remote DB — the constraint is SQLite-only, local.
- `pnpm dev` (port 3000) as the test/demo run path — `basePath: '/app'` causes 404 at `localhost:3000/`; always use the single-origin path via FastAPI at port 8001.

## Deployment Model

Local development server only (no cloud deployment in scope). Single process: `uv run python -m src` starts FastAPI + Uvicorn on port 8001. The frontend must be pre-built (`cd frontend && pnpm build`) before starting the backend for the full UI to appear.

> **Assumed:** `pandas` is not yet in `pyproject.toml`; the code-generator for slice-a adds it to `[project.dependencies]`.

> **Assumed:** `matplotlib` is not yet in `pyproject.toml`; it is added in the Phase 2 slice-a pass.

> **Assumed:** `python-multipart` is already present (required by FastAPI upload); if missing, slice-a adds it.

> **Assumed:** The existing `src/llm/client.py` and `src/llm/providers/gemini.py` are used as-is by the `answer_question` node (and `generate_code` node in Phase 2). The `DEFAULT_MODEL` in `gemini.py` is updated from `gemini-2.5-flash` to `gemini-2.0-flash`.
