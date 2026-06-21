# python-fastapi-sqlite

Starter scaffold for a Python + FastAPI + LangGraph agent with a **local-first
relational store — SQLite**. Schema is bootstrapped with `create_tables()` at
startup (no migrations shipped; add Alembic when you need schema evolution).

Runs **green offline**: no server to stand up, no API key. The LLM defaults to a
stub and the database is a local SQLite file via `aiosqlite`.

The executor copies this into `src/`, `tests/`, and the project root, then adapts
it to the spec. Delete this directory after copying.

---

## What's here

```
pyproject.toml          uv project — deps, pytest config, ruff
.env.example            APPNAME_ settings — stub LLM, SQLite, port 8001

src/
  config.py             pydantic-settings — APPNAME_ prefix, SecretStr, stub flag
  __main__.py           uvicorn entry point — port 8001
  api/
    app.py              FastAPI app factory + lifespan (calls init_db) + CORS
    health.py           GET /health — returns env, provider, stub_mode
  db/
    base.py             DeclarativeBase
    models.py           example Run model (id, input, result, created_at)
    session.py          async engine + AsyncSessionLocal + init_db() create_all
  agent/
    state.py            AgentState TypedDict — run_id, input, history, result, error
    graph.py            LangGraph graph — plan_action → invoke_tool ↺ → finalize/error
    nodes.py            plan_action, invoke_tool, finalize, handle_error
    tools.py            Tool dataclass + TOOL_REGISTRY + register()
  integrations/
    llm.py              thin LLM client — routes to provider or stub
    stubs/
      llm.py            stub LLM — canned ReAct responses, no API key needed

tests/
  conftest.py           offline kill-switch + throwaway SQLite db_session fixture
  unit/
    test_health.py      GET /health → 200, stub_mode is True
    test_models.py      create + read a Run row on SQLite
```

## Schema bootstrap

`init_db()` (called from the app's lifespan) imports `src.db.models` so every
table registers on `Base.metadata`, then runs `Base.metadata.create_all`. This is
the only schema step — there are **no migrations shipped**. When the schema needs
to evolve, add Alembic at that point.

## Quickstart

```bash
uv sync --extra dev
cp .env.example .env          # defaults run offline on SQLite with the stub LLM
uv run python -m src          # server starts on :8001
curl http://localhost:8001/health   # {"status":"ok","stub_mode":true,...}
```

## How to use

1. Copy `pyproject.toml`, `.env.example` to the project root
2. Copy `src/` to `src/` and `tests/` to `tests/`
3. Replace every occurrence of `appname` / `APPNAME` with the project name
4. Add project-specific models to `src/db/models.py`, routes to `src/api/`, tools
   to `src/agent/tools.py`
5. Delete this recipe directory from the project

## Gate

```bash
uv run pytest -q          # green offline — SQLite, stub LLM, no key, no network
```

---

_stamped 2026-06-22_
