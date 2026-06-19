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
- **Database:** **local-first.** The Phase-1 default is **SQLite** (via `aiosqlite`) for app metadata +
  agentic entities, and **DuckDB** where the work is analytical (querying uploaded tabular data). Phase 1
  should run on one machine with no external service to stand up. **PostgreSQL is a later
  "productionising" capability** (multi-user, durable, `pgvector`-ready) — reached for when a project
  outgrows local, not the initial build's default. Same SQLAlchemy 2.0 code either way; moving to
  Postgres is a driver/URL change. (Honor PostgreSQL if the user explicitly asks for it at intake.)
- **LLM provider:** **chosen at intake** (`agent-builder` Q4, paired with its API key) — Anthropic /
  OpenAI / Gemini / OpenRouter / other. No hardcoded default; Anthropic is the recommendation, not an
  assumption.
- **Dependency management:** `uv` + `pyproject.toml` (Python); `pnpm` or `npm` (Node.js).

This is the stack the intake questions (`agent-builder` Q2 stack, Q4 provider) recommend first. The agentic layers built on
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

| Provider | Default | Cheap / fast | Hard reasoning | Notes |
|----------|---------|--------------|----------------|-------|
| **Anthropic** (recommended) | `claude-sonnet-4-6` | `claude-haiku-4-5-20251001` | `claude-opus-4-8` | `claude-fable-5` also available |
| Google Gemini | `gemini-2.5-flash` | `gemini-2.5-flash` | `gemini-2.5-pro` | older `1.5`/`2.0-flash` unavailable to new users |
| OpenAI | `gpt-4o-mini` | `gpt-4o-mini` | `gpt-4o` | |

## Agentic Stack Tech (source of truth for layers 2–9)

Defaults for the layers in [`agentic-architecture.md`](agentic-architecture.md). Zero-ops choices first;
the override column is what to reach for at scale. The tech-designer pins the actual choice per project.

| Layer | Default | Override at scale |
|-------|--------------------|-------------------|
| Orchestration | **LangGraph** (`StateGraph`) | — (Claude Agent SDK for Claude-native/light) |
| Model client | **LangChain `init_chat_model`** (provider-agnostic) | direct provider SDK if a feature needs it |
| Tools / integration | **MCP everywhere** via `mcp` SDK (stdio) — internal *and* external tools | MCP over streamable HTTP; official servers |
| Memory store | **SQLite** tables (`memory_records`) — local default | PostgreSQL (+ partitioning) when productionising |
| Vector / embeddings | **`sqlite-vec`** + provider/local embeddings — local default | `pgvector`, then a dedicated vector DB (Qdrant/Weaviate) |
| Retrieval rerank | none (top-k) | cross-encoder / LLM reranker |
| Checkpointer (durability) | **`SqliteSaver`** — local default | `PostgresSaver` when productionising |
| Guardrails | in-process validators + Pydantic | a dedicated guardrails lib if policy grows |
| Tracing | **OTel GenAI** spans (baseline) → LangSmith / Langfuse / OTLP | aggregate metrics + latency dashboards |
| Evals | `pytest` + a fixed dataset, real model, loose asserts | LLM-judge + component evals + online judges |

**Raised baseline (real, Phase 1):** the default agent ships layers 1–4 + 9 (model, context,
working/short-term memory, MCP tools, observability + OTel tracing + an eval skeleton) — **real, not
stubbed**, from Phase 1. Layer 5 (retrieval/RAG), layer 6 (multi-agent), layer 7 (HITL), layer 8
(durable execution), and long-term memory are added when they earn their place. See [`phases.md`](phases.md).

---

## To fill in (tech-designer)

### Language & Runtime
<!-- FILL IN: e.g. Python 3.12 async backend; Node.js 20 frontend. Default stack above unless overridden. -->
**Why:** <!-- reason -->

### Agent Framework
<!-- FILL IN: LangGraph (conditional routing / checkpointing) · simple loop · none -->
**Why:** <!-- reason -->

### LLM Provider & Model
<!-- FILL IN: provider chosen at intake + a specific model from the Models table above; built via
     init_chat_model. -->
**Why:** <!-- reason -->

### Backend Framework
<!-- FILL IN: async FastAPI (Python, recommended) · Express · none -->

### Database & ORM
<!-- FILL IN: local-first — SQLite (default) + DuckDB where analytical; PostgreSQL only if the user
     asked for it (it's a later productionising step). See § Database & Tests. ORM: async SQLAlchemy 2.0
     (aiosqlite for SQLite, asyncpg for Postgres). -->

### Frontend
<!-- FILL IN: Node.js only — Next.js 15 + React + TailwindCSS (default). Never Python. -->

### Key Libraries
<!-- FILL IN: HTTP client, LLM client, ORM, testing, logging, integration-specific libs. -->

| Library | Version | Purpose |
|---------|---------|---------|
| | | |

### What to Avoid
<!-- FILL IN: libraries/patterns explicitly off-limits and why. -->

---

## Permanent Rules (all projects)

### Database & Tests (canonical home)

- **Driver in main dependencies.** The DB driver (e.g. `psycopg2-binary` for PostgreSQL) goes in
  `[project.dependencies]`, never a dev-only group. Alembic migrations run at deploy/setup time, not
  just in tests — a dev-only driver makes `alembic upgrade head` fail wherever dev deps aren't installed.
- **Tests use the same driver as production.** Since the Phase-1 default is SQLite, tests run against
  SQLite (a file-backed `_test.db`) — that is correct, not a shortcut. If a project has productionised
  to PostgreSQL, its tests run against PostgreSQL; tests that only pass on a different driver than
  production are not a passing gate.
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
