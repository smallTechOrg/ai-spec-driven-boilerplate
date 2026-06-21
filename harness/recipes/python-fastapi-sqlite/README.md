# python-fastapi-sqlite

A generic, domain-neutral **agent starter**: Python + FastAPI + LangGraph ReAct
loop, behind a thin LLM client (stub by default), with a **local-first
relational store — SQLite**. It runs **green out of the box** from a fresh copy —
no API key, no server to stand up, fully offline.

The example capability is a single trivial `echo` tool, clearly marked
**[REPLACE ME]**. It exists only to wire the full vertical slice end to end so
you can see every seam working, then swap it for your real agent.

The canonical UI is the Next.js agent-chat recipe; this recipe also ships a
no-JS Jinja fallback that drives the same slice.

---

## What's here

```
pyproject.toml          uv project — deps, pytest config, ruff, optional `llm` extra
.env.example            APPNAME_ settings — stub LLM, SQLite, port 8000
.gitignore              keeps runtime artifacts (*.db, .venv, etc.) out of git

src/
  __init__.py  __main__.py  config.py
  config.py             pydantic-settings — APPNAME_ prefix, SecretStr, stub flag
  __main__.py           uvicorn entry point — host/port from settings
  api/
    app.py              FastAPI app factory + lifespan (init_db) + configurable CORS
    health.py           GET /health — env, provider, stub_mode
    routes.py           POST /api/run — JSON contract the Next.js UI calls
    ui.py               no-JS Jinja fallback (drives the same slice)
    templates/{base,index}.html
  agent/
    state.py            AgentState TypedDict — run_id, user_input, tool_call_history,
                        result, error, iterations (a PLAIN list — no add_messages)
    graph.py            LangGraph graph — plan_action → invoke_tool ↺ → finalize/error
    nodes.py            plan_action, invoke_tool, finalize, handle_error
    tools.py            Tool dataclass + TOOL_REGISTRY + the example echo tool [REPLACE ME]
  db/
    base.py             DeclarativeBase
    models.py           example Run model (id, input, result, created_at)
    session.py          async engine + AsyncSessionLocal + init_db() create_all
  integrations/
    llm.py              thin LLM client — routes stub | anthropic
    _anthropic.py       the single real provider (anthropic SDK, claude-sonnet-4-6)
    stubs/
      llm.py            stub LLM — canned ReAct script, no API key needed

tests/
  conftest.py           offline kill-switch + throwaway SQLite db_session fixture
  unit/
    test_health.py      GET /health → 200, stub_mode True
    test_agent_loop.py  full stub ReAct loop via the echo tool (offline)
    test_run_api.py     POST /api/run → {ok, data:{result, run_id}} + persists a Run
    test_models.py      create + read a Run row on SQLite
```

## The vertical slice

`POST /api/run` with `{ "input": "<text>" }` drives:

```
UI → API → LangGraph ReAct loop → echo tool → stub LLM → SQLite persistence → response
```

and returns `{ "ok": true, "data": { "result": "<string>", "run_id": <id> } }`.
Everything is generic placeholder. The executor deletes the echo tool + stub and
wires the real agent without re-plumbing the slice.

## Quickstart

```bash
uv sync --extra dev
cp .env.example .env          # defaults run offline on SQLite with the stub LLM
uv run pytest -q              # green offline — no key, no network
uv run python -m src          # server starts on 127.0.0.1:8000
curl http://localhost:8000/health   # {"status":"ok","stub_mode":true,...}
```

## Going live

The default provider is `stub` (no key). To use the real Anthropic provider:

```bash
uv sync --extra llm           # installs the `anthropic` SDK
# in .env:
#   APPNAME_LLM_PROVIDER=anthropic
#   APPNAME_ANTHROPIC_API_KEY=sk-ant-...
#   APPNAME_LLM_MODEL=claude-sonnet-4-6   (default)
```

Switching provider/model/DB is a config change, never a code change.

## Rename the project

There is **one** placeholder token, used consistently everywhere:

- `appname` (lowercase) — the project / package / distribution name. Appears in
  `pyproject.toml` `[project].name`, FastAPI `title="appname"`, the Jinja
  `<title>`/`<h1>`, and `appname.db`.
- `APPNAME` (uppercase) — the env-var prefix ONLY. Appears in `.env.example` and
  pydantic-settings `env_prefix="APPNAME_"` (e.g. `APPNAME_LLM_PROVIDER`,
  `APPNAME_DATABASE_URL`, `APPNAME_PORT`).

Copy-paste, from the project root after copying the recipe in:

```bash
# macOS:
grep -rl 'appname\|APPNAME' . | xargs sed -i '' 's/APPNAME/MYAPP/g; s/appname/myapp/g'
# linux:
grep -rl 'appname\|APPNAME' . | xargs sed -i 's/APPNAME/MYAPP/g; s/appname/myapp/g'
```

## How to use

1. Copy `pyproject.toml`, `.env.example`, `.gitignore` to the project root.
2. Copy `src/` to `src/` and `tests/` to `tests/`.
3. Run the rename step above.
4. Replace the example `echo` tool in `src/agent/tools.py` with your real tools,
   the stub in `src/integrations/stubs/llm.py` (or switch the provider to
   `anthropic`), and extend `src/db/models.py` / `src/api/` as needed.
5. **Delete this recipe directory from the project.**

## Gate

```bash
uv run pytest -q && uv run ruff check
```

---

_stamped 2026-06-22 — fastapi>=0.115, langgraph>=0.2, sqlalchemy[asyncio]>=2.0,
pydantic-settings>=2.0, anthropic>=0.40 (llm extra), python>=3.12_
