# python-fastapi-duckdb

A generic, domain-neutral **agent starter** — FastAPI + LangGraph + a **DuckDB
columnar storage seam** alongside the SQLite relational spine. It runs **green out
of the box** from a fresh copy: no server to stand up, no API key. The LLM defaults
to a stub and persistence is local files.

This recipe and **python-fastapi-sqlite** share ONE packaged layout — they differ
ONLY in `src/db/` (this one adds a generic DuckDB event-store seam) and the one
example write to that store. Everything else (`src/api/`, `src/agent/`,
`src/integrations/`) is the same shape.

The executor copies this into `src/`, `tests/`, and the project root, then adapts
it to the spec. **Delete this recipe directory after copying.**

---

## What's here

```
pyproject.toml          uv project — deps, pytest config, ruff
.env.example            APPNAME_ settings — stub LLM, SQLite spine, DuckDB seam, port 8000
.gitignore              keeps *.db / *.duckdb / data/ / .env out of git

src/
  config.py             pydantic-settings — APPNAME_ prefix, SecretStr, stub flag
  __main__.py           uvicorn entry point — host/port from settings
  api/
    app.py              FastAPI app factory + lifespan (init_db) + configurable CORS
    health.py           GET /health — env, provider, stub_mode
    ui.py               GET / chat UI + POST /run no-JS form fallback
    routes.py           POST /api/run — JSON contract {ok, data:{result, run_id}}
    run.py              run_agent — graph -> echo -> persist Run -> DuckDB event
    templates/          base.html + index.html (stub banner, four UI states)
  agent/
    state.py            AgentState TypedDict (plain list — no add_messages reducer)
    graph.py            LangGraph ReAct graph — plan_action ↺ invoke_tool -> finalize
    nodes.py            plan_action, invoke_tool, finalize, handle_error
    tools.py            Tool registry + the echo [REPLACE ME] example tool
    observability.py    span() context manager (structured-log span)
  db/                   THE storage layer (the only thing that differs from sqlite)
    base.py             DeclarativeBase
    models.py           example Run model (id, input, result, created_at)
    session.py          async engine + AsyncSessionLocal + init_db()
    duck.py             generic DuckDB event-store seam (one columnar events table)
  integrations/
    llm.py              thin LLMClient — routes stub | anthropic
    _anthropic.py       the real provider (anthropic SDK, claude-sonnet-4-6)
    stubs/llm.py        stub LLM — echo then FINAL_ANSWER, no key needed

tests/
  conftest.py           offline kill-switch + throwaway SQLite + temp DuckDB dir
  unit/
    test_health.py      GET /health -> 200, stub_mode True
    test_agent_loop.py  full stub ReAct loop via the echo tool
    test_run_api.py     POST /api/run -> {ok, data} and a persisted Run row
    test_models.py      Run create+read on SQLite; one DuckDB event write/read
```

## The example capability (REPLACE ME)

A single trivial tool, `echo(text) -> "echo: {text}"`, is the ONLY registered tool
(`src/agent/tools.py`, clearly marked `[REPLACE ME]`). The stub LLM
(`src/integrations/stubs/llm.py`) drives it end to end: first call invokes `echo`
with the user input, then — once one tool result is in history — returns a generic
`FINAL_ANSWER`. This makes the full wiring visible
(UI -> API -> graph -> echo tool -> stub LLM -> SQLite persistence -> DuckDB event
-> response) while being obviously a placeholder. Swap the echo tool + stub for your
real capability without rewiring the slice.

## The storage layer (what differs from the sqlite recipe)

`src/db/session.py` bootstraps the SQLite spine (the `runs` table) AND the DuckDB
seam. `src/db/duck.py` is a tiny generic event store: one columnar `events` table,
`append_event` / `read_events`. The example route writes the echo result there to
demonstrate the DuckDB storage layer — there is no file upload, no SQL generation,
no schema introspection. `[REPLACE ME]` it with your real columnar workload.

## Quickstart

```bash
uv sync --extra dev
cp .env.example .env          # defaults run offline: SQLite + DuckDB + stub LLM, no key
uv run python -m src          # serves on 127.0.0.1:8000
curl http://localhost:8000/health        # {"status":"ok","stub_mode":true,...}
# open http://localhost:8000  -> chat UI with a visible stub banner
```

The real LLM path is optional: `uv sync --extra llm`, then set
`APPNAME_LLM_PROVIDER=anthropic` and `APPNAME_ANTHROPIC_API_KEY` in `.env`.
Switching provider/model/DB is a config change, never a code change.

## Rename the project

ONE placeholder token renames the whole project with a single find-replace:

- `appname` (lowercase) — the project/package/distribution name. Appears in
  `pyproject.toml` `[project].name`, FastAPI `title`, the Jinja `<title>`/`<h1>`.
- `APPNAME` (uppercase) — the env-var prefix ONLY (`.env.example` and
  `pydantic-settings` `env_prefix="APPNAME_"`).

```bash
# from the project root, after copying the recipe in:
grep -rl 'appname\|APPNAME' . | xargs sed -i '' 's/APPNAME/MYAPP/g; s/appname/myapp/g'   # macOS
# linux: sed -i 's/APPNAME/MYAPP/g; s/appname/myapp/g'
```

Then delete this recipe directory.

## Gate

```bash
uv run pytest -q && uv run ruff check
# green offline — SQLite + DuckDB, stub LLM, no key, no network
```

---

_stamped 2026-06-22 — fastapi>=0.115, langgraph>=0.2, langchain-core>=0.3,_
_sqlalchemy[asyncio]>=2.0, duckdb>=1.0, pydantic-settings>=2.0, python>=3.12_
