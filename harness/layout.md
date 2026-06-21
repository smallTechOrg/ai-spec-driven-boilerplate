# Project Layout

The repository root holds the four layers plus the `.claude/` adapter and project config.
These conventions are language-neutral at the harness level; Python specifics are noted
where they are the established default.

---

## Where things go

- **All application source code lives in `src/`** — never at the repo root, for every
  stack (backend, frontend, scripts, data pipelines).
- **Tests live in `tests/` at the repo root** — co-located with `src/`, not inside it.
  (Python/pytest convention; stack recipes may vary for other languages.)
- **Outcome goes to `logs/`** — `runtime/` is gitignored (live data); `sessions/` and
  `analysis/` are **committed** (the durable record of decisions and the analyser's drift findings).
  `logs/PLAN.md` is the live coordination hub for the **current phase** (Step DAG +
  Progress Tracker + Phase Acceptance) — a single hardcoded path every sub-agent opens
  without being told its name; ephemeral, rewritten whole by the planner at the start of
  each phase, and may stay gitignored.
  (Note: `.gitignore` currently ignores all of `logs/`; for `sessions/` and `analysis/`
  to be committed as stated, add negation rules — `logs/PLAN.md` may remain ignored.)
- **The spec is the contract** — `src/` conforms to `spec/`, never the reverse. `spec/`
  holds exactly the seven product-spec docs above and **no live execution state** (that
  lives in `logs/PLAN.md`).

---

## Repo skeleton

```
spec/            the product spec — exactly seven docs, no live state
  vision.md       what it is, who it's for, the goal
  architecture.md the shape of the system
  data-model.md   entities and their relationships
  api.md          the interface contract
  ui.md           the user-facing surface
  agent-graph.md  the agent loop, nodes, graph
  delivery-plan.md the durable phase roadmap — ordered phases, per-phase EARS
                  criteria (PN-ACn), inter-phase deps. Edited only on a real spec change.

src/             all application code
  agent/         agent loop, nodes, graph assembly (LangGraph projects)
  api/           HTTP layer (FastAPI routers, request/response models)
  db/            DB models, migrations, session factory
  integrations/  thin clients for external providers (LLM, APIs)
    stubs/       offline stubs — used in Phase 2, replaced in Phase 3+
  ui/            frontend (Next.js or templates)
  config.py      pydantic-settings config, loaded once at startup

tests/           all tests
  unit/          fast, no network, no DB
  integration/   requires DB; automated setup via conftest.py
  e2e/           golden-path smoke tests
evals/           golden cases (input + approved output) + threshold + runner — same defs local/gate/CI

logs/            PLAN.md (current-phase Step DAG + Progress Tracker + Phase Acceptance —
                 the single hardcoded coordination path; ephemeral, rewritten per phase) ·
                 runtime/ (gitignored, live data) · sessions/ + analysis/ (committed)
harness/         the method — rules/, process/, patterns/, recipes/
.claude/         thin Claude Code adapter
CLAUDE.md        entry point
README.md        what this project is — overview, setup, usage, config, dev
```

---

## Python project conventions

These apply to all Python builds using this harness:

- **Package manager:** `uv` — dependencies in `pyproject.toml`
- **Entry point:** `src/__main__.py` — starts the server on port 8001
- **Config:** `src/config.py` using `pydantic-settings`; loaded once, validated at startup
- **Schema:** `create_tables()` at startup (SQLAlchemy `create_all`) — no migrations shipped;
  add `alembic` only if you need schema evolution
- **Tests:** `uv run pytest` from the repo root
- **Linting:** `uv run ruff check .`
- **Stubs:** `APPNAME_LLM_PROVIDER=stub` env var enables stub mode; stub mode adds a
  visible banner on every UI page

## Rules

1. Application code in `src/`; tests in `tests/`; never at the root.
2. One concern per module — no god-files.
3. Prompts and templates are data files loaded at runtime, not inlined in code.
4. External services (LLM, DB, APIs) sit behind a thin client in `src/integrations/` —
   never called raw from business logic.
5. The stub steps must run fully offline — no API keys, no network I/O.
6. `README.md` must always be accurate: every command works exactly as written from the
   directory stated.
