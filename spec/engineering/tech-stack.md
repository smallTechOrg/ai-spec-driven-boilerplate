# Tech Stack

> **Boilerplate status:** The FILL-IN sections are completed by the tech-designer sub-agent after the
> product spec is approved. The user may override any choice; a stated preference is always binding
> (see `.claude/agents/tech-designer.md`). The **Permanent Rules** at the bottom apply to all projects.

---

## Default Stack (when the user states no preference)

- **Backend / agent:** Python 3.12+, **async** — agent logic, data processing, API server. The API is
  async FastAPI and the DB layer is **async SQLAlchemy** (`asyncpg` / `aiosqlite` driver); the agent
  loop is `async def` throughout. Async is the default, not an upgrade.
- **Frontend:** Node.js 20+ — **Next.js 15 + React + TailwindCSS**. **The frontend is always Node.js,
  never Python.** There is no Python frontend option; any UI/web surface is Node.js regardless of backend.
- **Database:** **PostgreSQL for any real project** (multi-user, durable, `pgvector`-ready). SQLite is
  for quick demos/prototypes only. Same SQLAlchemy 2.0 code either way — it's a driver/URL change.
- **LLM provider:** **chosen at intake** (`agent-builder` Q-provider) — Anthropic / OpenAI / Gemini /
  OpenRouter / other. No hardcoded default; Anthropic is the recommendation, not an assumption.
- **Dependency management:** `uv` + `pyproject.toml` (Python); `pnpm` or `npm` (Node.js).

This is the stack the intake question (`agent-builder` Q2) recommends first. The agentic layers built on
top of it are speced in [`agentic-architecture.md`](agentic-architecture.md); their exact tech is the
**Agentic Stack Tech** table below.

## Models (source of truth — every other file links here)

Always use a current, verified model name — never a guessed or deprecated one. The name must be
configurable via an env var (e.g. `APP_LLM_MODEL`) so it changes without a code deploy. A 404
`NOT_FOUND` from an LLM API almost always means a wrong/deprecated model name — check the name first.
Verify against the provider's current docs / `ListModels` before hardcoding.

The provider is chosen at intake (→ [`patterns/llm-providers.md`](patterns/llm-providers.md)); the model
is constructed with LangChain `init_chat_model`, so switching is a config change. Pick the default +
cheap + strong row for whichever provider the user chose.

**This project's chosen provider is Google Gemini** (selected at intake — this overrides the
Anthropic recommendation default). The default model is `gemini-2.5-flash`; the hard-reasoning model is
`gemini-2.5-pro`. Built via `init_chat_model(model_provider="google_genai")` using
`langchain-google-genai`, which authenticates with **`GOOGLE_API_KEY`** (set `GEMINI_API_KEY` to the
same value for clarity; the SDK reads `GOOGLE_API_KEY`). See § LLM Provider & Model below.

| Provider | Default | Cheap / fast | Hard reasoning | Notes |
|----------|---------|--------------|----------------|-------|
| **Google Gemini** (chosen for this project) | `gemini-2.5-flash` | `gemini-2.5-flash` | `gemini-2.5-pro` | provider = `google_genai`; key = `GOOGLE_API_KEY`; older `1.5`/`2.0-flash` unavailable to new users |
| Anthropic | `claude-sonnet-4-6` | `claude-haiku-4-5-20251001` | `claude-opus-4-8` | `claude-fable-5` also available |
| OpenAI | `gpt-4o-mini` | `gpt-4o-mini` | `gpt-4o` | |

## Agentic Stack Tech (source of truth for layers 2–9)

Defaults for the layers in [`agentic-architecture.md`](agentic-architecture.md). Zero-ops choices first;
the override column is what to reach for at scale. The tech-designer pins the actual choice per project.

| Layer | Default | Override at scale |
|-------|--------------------|-------------------|
| Orchestration | **LangGraph** (`StateGraph` ReAct loop) | — (Claude Agent SDK for Claude-native/light) |
| Model client | **LangChain `init_chat_model("gemini-2.5-flash", model_provider="google_genai")`** via `langchain-google-genai` | direct provider SDK if a feature needs it |
| Tools / integration | **MCP everywhere** via `mcp` SDK (stdio) — SQL-query + schema-inspect tools, read-only enforced at the action-safety boundary | MCP over streamable HTTP; official servers |
| Memory store | PostgreSQL tables (`memory_records`); SQLite for demos | PostgreSQL + partitioning |
| Vector / embeddings | **`pgvector`** + provider or local embeddings (`sqlite-vec` for demos) | a dedicated vector DB (Qdrant/Weaviate) |
| Retrieval rerank | none (top-k) | cross-encoder / LLM reranker |
| Checkpointer (durability) | **`PostgresSaver`** (`SqliteSaver` for demos) | — |
| Guardrails | in-process validators + Pydantic | a dedicated guardrails lib if policy grows |
| Tracing | **OTel GenAI** spans (baseline) → LangSmith / Langfuse / OTLP | aggregate metrics + latency dashboards |
| Evals | `pytest` + a fixed dataset, real model, loose asserts | LLM-judge + component evals + online judges |

**Raised baseline (real, Phase 1):** the default agent ships layers 1–4 + 9 (model, context,
working/short-term memory, MCP tools, observability + OTel tracing + an eval skeleton) — **real, not
stubbed**, from Phase 1. Layer 5 (retrieval/RAG), layer 6 (multi-agent), layer 7 (HITL), layer 8
(durable execution), and long-term memory are added when they earn their place. See [`phases.md`](phases.md).

---

## To fill in (tech-designer)

> **Project:** a data-analysis agent. Users upload CSV files into a dataset, then ask questions in
> natural language over a multi-turn chat; the agent answers in text plus result tables. Charts,
> insights, and structured JSON output are deferred to a later phase.

### Language & Runtime
**Backend / agent:** async Python 3.12+ (LangGraph agent + FastAPI API server, async throughout).
**Frontend:** Node.js 20 — Next.js 15 + React + TailwindCSS chat UI.
**Why:** The data work (CSV parsing, schema inference, columnar query) and the LangGraph + LangChain
agentic ecosystem are strongest in async Python; the frontend is always Node.js (there is no Python
frontend). Both are user-stated, binding choices.

### Agent Framework
**LangGraph** — a `StateGraph` ReAct loop (plan_action → execute_action → observe), terminating on a
structured `finish` tool.
**Why:** A data-analysis agent acts on the outside world (it runs SQL over the uploaded data), so it
needs the ReAct loop, not a one-shot pipeline — it must inspect the schema, draft a query, see the
result, and self-correct on a bad query. LangGraph gives explicit state, conditional routing
(action vs. finish vs. error vs. force_finalize), and a clean seam for a checkpointer later. Binding
user choice.

### LLM Provider & Model
**Google Gemini** (chosen at intake — overrides the Anthropic recommendation). Default
`gemini-2.5-flash`; hard-reasoning `gemini-2.5-pro`. Constructed via
`init_chat_model("gemini-2.5-flash", model_provider="google_genai")` from `langchain-google-genai` —
**no bespoke `LLMClient` wrapper**, real-first with no stub/offline mode. Auth key:
**`GOOGLE_API_KEY`** (the `langchain-google-genai` SDK reads `GOOGLE_API_KEY`; set `GEMINI_API_KEY` to
the same value as the documented alias). Model name and provider are env-configurable
(`APP_LLM_MODEL`, `APP_LLM_PROVIDER`) so switching is a config change.
**Why:** Binding user choice. Gemini Flash is fast and cheap for the per-turn plan/observe calls of the
ReAct loop; Pro is reserved for harder reasoning steps.

### Backend Framework
**async FastAPI** + Uvicorn, with **SSE streaming** for the chat response (so the live `action_history`
trace — each step's plain-English description, then the answer + result table — streams to the UI).
Errors return as JSON via the response envelope, never an HTML page. Runs on **port 8001**.

### Database & ORM
**Two stores, distinct roles — do not conflate them:**

- **SQLite** (binding user override — demo/single-machine) — app metadata and agentic entities:
  datasets, uploaded-file metadata, chat sessions, `runs`, `messages`. Accessed via **async
  SQLAlchemy 2.0 + `aiosqlite`**, migrations via **Alembic**. This is the durable system-of-record. The
  same SQLAlchemy 2.0 code moves to PostgreSQL by changing only the driver/URL if the project outgrows a
  single machine. Tests run against SQLite (same driver as production — correct per § Database & Tests).
- **DuckDB** — the **analytical query engine** that executes the agent's read-only SQL over the
  uploaded CSV data (in-process, fast columnar). DuckDB holds the *data being analyzed*; it is not the
  app's metadata store. CSVs are parsed with **pandas** for schema inference and a small sample; the
  full dataset is queried in DuckDB, never sent to the LLM.

### Frontend
**Node.js 20 — Next.js 15 + React + TailwindCSS.** A multi-turn chat UI: file upload into a dataset,
a message thread, streamed agent steps (live action trace), and rendered result tables. Talks to the
FastAPI backend over HTTP + SSE. Dependencies via `npm`/`pnpm`. Never Python.

### Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `python` | `>=3.12` | Backend/agent runtime (async) |
| `fastapi` | `>=0.115` | Async API framework |
| `uvicorn[standard]` | `>=0.32` | ASGI server (port 8001) |
| `sse-starlette` | `>=2.1` | SSE streaming of the chat response / live action trace |
| `python-multipart` | `>=0.0.12` | CSV file upload (multipart form parsing) |
| `sqlalchemy[asyncio]` | `>=2.0` | Async ORM for SQLite metadata |
| `aiosqlite` | `>=0.20` | Async SQLite driver (in `[project.dependencies]`, not dev-only) |
| `alembic` | `>=1.14` | Database migrations |
| `duckdb` | `>=1.1` | In-process columnar engine — runs read-only SQL over uploaded CSVs |
| `pandas` | `>=2.2` | CSV parsing, schema inference, sampling rows for the LLM |
| `pydantic` | `>=2.9` | Typed models at module boundaries |
| `pydantic-settings` | `>=2.6` | Env/config loading (`extra="ignore"`, strip inline comments) |
| `langgraph` | `>=0.2.50` | StateGraph ReAct orchestration |
| `langchain` | `>=0.3` | `init_chat_model` + tool/message abstractions |
| `langchain-google-genai` | `>=2.0` | Gemini provider for `init_chat_model` (`google_genai`) |
| `mcp` | `>=1.1` | MCP SDK — SQL-query + schema-inspect tools (stdio), read-only |
| `structlog` | `>=24.4` | Structured JSON logs bound to `run_id` |
| `opentelemetry-sdk` + `opentelemetry-api` | `>=1.28` | OTel GenAI traces (token/cost spans) — baseline observability |
| `pytest` | `>=8.3` | Test runner |
| `pytest-asyncio` | `>=0.24` | Async test support (`asyncio_mode = "auto"`) |
| `httpx` | `>=0.27` | Async test client for FastAPI |
| `playwright` | `>=1.48` | Browser / E2E tests (later phase) |
| `next` | `^15` | Frontend framework (Node.js) |
| `react` | `^19` | UI library |
| `tailwindcss` | `^3.4` | Styling |

Pin exact versions in `pyproject.toml` / `package.json` at scaffold time; the ranges above are floors.
Verify the Gemini model name against `ListModels` before hardcoding — a 404 `NOT_FOUND` means a
wrong/deprecated model name.

### What to Avoid
- **No stub / offline LLM mode**, no `provider=auto`. Every model call is the real Gemini API; the key
  is required in every environment including CI (loose assertions absorb output variance).
- **No bespoke `LLMClient` wrapper** — use `init_chat_model` directly through one thin module-level
  accessor.
- **No repository pattern** — use direct async SQLAlchemy 2.0 in the service/node layer; no
  per-entity repository classes.
- **No write / DDL SQL from the agent.** DuckDB queries are **read-only, SELECT-only**, enforced at the
  action-safety boundary (AST/parse check — reject `INSERT`/`UPDATE`/`DELETE`/`CREATE`/`DROP`/`ATTACH`/
  `COPY`/`INSTALL`/`LOAD`, etc.). The MCP SQL tool never mutates data.
- **Never send the full dataset to the LLM** — pass only the inferred schema plus a small sample of
  rows; the data lives in DuckDB and is queried there.
- **Don't conflate the two stores** — SQLite is metadata/agentic entities, DuckDB is the analytical
  data. Don't run app metadata through DuckDB or push CSV rows into SQLite.

---

## Permanent Rules (all projects)

### Database & Tests (canonical home)

- **Driver in main dependencies.** The DB driver (e.g. `psycopg2-binary` for PostgreSQL) goes in
  `[project.dependencies]`, never a dev-only group. Alembic migrations run at deploy/setup time, not
  just in tests — a dev-only driver makes `alembic upgrade head` fail wherever dev deps aren't installed.
- **Tests use the same driver as production.** If production is PostgreSQL (the default for real
  projects), tests run against PostgreSQL — tests that only pass on SQLite are not a passing gate. If
  production is SQLite (demos), SQLite tests are correct.
- **Test DB is set up automatically** via `conftest.py` (`Base.metadata.create_all` against the test DB
  URL, dropped after). No manual steps. The URL comes from an env var (`TEST_DATABASE_URL`, or a
  `_test` database via `DATABASE_URL`), provided by a gitignored `.env.test` or a CI variable, and the
  README documents it.
- **The LLM is real in tests** — the API key is set (locally from `.env`, in CI from a secret). Tests
  assert loosely (structure + non-empty) to absorb output variance; there is no stub
  (`patterns/llm-providers.md`).

### Default Dev Port — 8001

All generated projects use **port 8001** (not 8000, which is commonly occupied by other local
services). `__main__.py` hard-codes `port=8001` unless an env var overrides it; the README references
`http://localhost:8001`; `.env.example` includes `PORT=8001` if configurable.

---

## Phase Gate Commands

`GOOGLE_API_KEY` must be set (locally from `.env`, in CI from a secret); `TEST_DATABASE_URL` points at a
file-backed `_test.db` SQLite database. Run from the repo root via `uv`.

| Phase | Gate command |
|-------|-------------|
| 1 | `uv run alembic upgrade head` (real SQLite) + `uv run pytest tests/test_agent_loop.py` (real Gemini — drives ≥2 ReAct iterations: one DuckDB query action, then `finish`; plus a force_finalize past `max_agent_iterations`) |
| 2 | `uv run pytest` (full suite: CSV upload → dataset, multi-turn chat over session, read-only SQL enforcement, MCP tools, SSE stream) |
| 3 | `uv run pytest && (cd frontend && npm test) && uv run pytest tests/e2e` (Playwright browser E2E: upload CSV, ask a question, see answer + result table) |
