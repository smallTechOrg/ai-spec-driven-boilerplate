# Recipe: python-fastapi-duckdb

A **conversational data-analysis agent** — ask a natural-language question about a CSV/JSON
dataset and get a grounded answer (plus an optional chart spec), produced by a ReAct tool loop
that writes and runs read-only SQL against your data.

**Stack:** FastAPI (serving + SSE token streaming) · LangGraph (the ReAct agent loop) ·
DuckDB (per-dataset analytical SQL) · SQLAlchemy async + SQLite (the metadata spine, runs,
spans, messages) · pydantic-settings (`APP_`-prefixed config) · LangChain `init_chat_model`
(provider-agnostic LLM accessor — default `google_genai` / `gemini-2.5-flash`).

The agent only ever issues **read-only** SQL (guardrails reject mutating statements), with row
and timeout caps. Every run records spans you can inspect at `/traces`.

> Source: re-homed from `feature/datachat-2026-06-19`, stamped 2026-06-22.

## Why it's green out of the box

It runs **fully offline with no API key**:
- The unit/integration suite drives the agent loop with an in-process `FakeModel` (no network).
- The server boots without a key — `/health` returns 200, the agent graph is simply not built
  until a key is present.
- The three **real-run** tests (live LLM) skip themselves automatically when `APP_LLM_API_KEY`
  is empty. Provide a funded key and they run.

## Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (package/venv manager)
- A Google Gemini API key — **only** for a real LLM run; not needed for tests or `/health`.

## Quickstart

```bash
# 1. install (runtime + dev/test toolchain)
uv sync --extra dev

# 2. config — copy the template; leave APP_LLM_API_KEY blank to stay offline,
#    or paste a Gemini key for real runs.
cp .env.example .env

# 3. run the tests (offline, no key, no network — FakeModel drives the loop)
uv run pytest

# 4. start the server
uv run python -m src
# open http://localhost:8001  (no-JS chat UI; /traces shows the run timeline)
```

Add `--extra llm` to `uv sync` when you want the real provider SDK (`langchain-google-genai`)
installed for live runs.

### Key routes
- `GET  /health` — liveness (200 offline)
- `POST /runs` — full run; returns `answer`, `run_id`, `thread_id`, `chart_spec`
- `POST /runs/stream` — same run as an SSE token stream
- `POST /upload`, `POST /datasets`, `POST /datasets/{id}/files` — ingest CSV/JSON
- `GET  /datasets`, `GET /datasets/{id}` — list / inspect schema
- `GET  /traces` — self-contained run + span timeline

## The gate (real run, needs a funded key)

End-to-end proof that a real run completes, the outcome + trajectory evals pass, and traces are
visible. Requires `APP_LLM_API_KEY` in `.env`:

```bash
./scripts/demo_gate.sh            # defaults to port 8001
# prints "DEMO GATE PASS" on success
```

The same real-run check is also available in-process as `tests/test_demo_gate.py` (skipped
without a key).

## Configuration

All settings are `APP_`-prefixed environment variables (see `src/config.py` and `.env.example`).
Switching LLM provider/model or the database is a **config change, never a code change** — only
`APP_LLM_PROVIDER` / `APP_LLM_MODEL` / `APP_DATABASE_URL` move.

## Layout

```
src/            the agent package (config, db, domain, duck, graph, runner, server, tools, …)
tests/          offline unit + integration suite (FakeModel); tests/e2e/ is Playwright, excluded
scripts/        demo_gate.sh — the real-run gate
pyproject.toml  deps + pytest config (e2e excluded from the default run)
.env.example    APP_-prefixed config template (no secrets)
```
