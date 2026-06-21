# Tech Stack (default — editable per project)

This is the default Zer0 stack. The architect/designer may change any of it during
intake; the user is encouraged to edit it directly. Whatever is recorded here is what
the engineer builds to. **This file is part of the spec (the goal), not the harness.**

## Defaults

| Concern  | Default                     | Notes |
|----------|-----------------------------|-------|
| Language | Python 3.12+                | Backend / agent runtime |
| Agent    | LangGraph                   | `StateGraph`; nodes are pure `(state) -> state` |
| API      | FastAPI                     | `create_app()` factory; thin routers |
| UI       | Next.js (Node.js)           | Only if the spec calls for a UI; else CLI/API only |
| Database | SQLite (default) / DuckDB   | Local-first; DuckDB for analytical workloads |
| LLM      | Anthropic Claude            | Behind a thin client; `provider=auto` (real when key set, stub otherwise) |
| Deploy   | Render (a later phase)      | Keep local-run simple; deploy after the build is reconciled |
| Pkg mgr  | uv (Python), npm/pnpm (Node)| All doc commands use the manager prefix (`uv run …`) |

## Gate commands (per stack)

The engineer and qa use these as phase gates (see `harness/rules/testing.md`):

| Stack          | Early gate                     | Skeleton gate |
|----------------|--------------------------------|---------------|
| Python (uv)    | `uv run pytest tests/unit`     | `uv run pytest` (offline; no LLM key) |
| Next.js (Node) | `npx vitest run`               | golden-path smoke test |

The skeleton phase must pass with **no LLM API key** set.

## Conventions tied to this stack

- All app code under `src/`; tests under `tests/` (repo root).
- External services (LLM, DB, HTTP) behind thin clients — never called raw in nodes.
- Prompts are `.md` files loaded at runtime, not inlined.
- Settings via env (Pydantic `BaseSettings` for Python); `.env.example` lists every var.
