# Tech Stack

Filled in by the researcher at intake. Defaults below apply to Python projects.
Override any line — the researcher proposes, the user approves.

---

## Language

**Python 3.12+** with `uv` as package manager.

Override: <!-- e.g. TypeScript 5 + Bun, if different -->

## Agent Framework

**LangGraph** — for any project with a reasoning loop or multi-step orchestration.  
**None** — for simple pipelines or pure API projects.

Override: <!-- e.g. CrewAI, custom -->

## LLM Provider

**Provider:** <!-- FILL IN: openai | anthropic | gemini -->  
**Model:** <!-- FILL IN: see safe defaults table below -->  
**Env var:** `APPNAME_LLM_MODEL` — always configurable, never hardcoded.

Safe defaults (2026):

| Provider | Default model |
|----------|--------------|
| Anthropic | `claude-3-5-haiku-latest` |
| OpenAI | `gpt-4o-mini` |
| Google Gemini | `gemini-2.5-flash` |

## Backend Framework

**FastAPI** — async, typed, fast.

Override: <!-- e.g. Django, Flask, none -->

## Database

**PostgreSQL** (production + tests).  
**SQLite / DuckDB** — local-only or analytics projects only.

**ORM:** SQLAlchemy 2.0 (async) + Alembic for migrations.

Override: <!-- e.g. MongoDB + Motor, if different -->

## Frontend

<!-- FILL IN: Next.js 15 / Jinja2 templates / none -->

Override if needed.

## Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| fastapi | latest | HTTP layer |
| sqlalchemy | 2.x | ORM |
| alembic | latest | migrations |
| pydantic-settings | latest | config |
| langgraph | latest | agent loop |
| pytest + pytest-asyncio | latest | tests |

Add project-specific libraries here at intake.

## What to Avoid

- SQLite as a test substitute for PostgreSQL
- Hardcoded model names (use env var)
- `git add -A` or committing `.env`
- Dev-only DB drivers (`psycopg2-binary` must be in `[project.dependencies]`)

---

## Permanent Rules

### Port: 8001

`src/__main__.py` starts on port **8001**. README and `.env.example` reference `http://localhost:8001`.

### DB driver in production dependencies

DB driver (`asyncpg`, `psycopg2-binary`) must be in `[project.dependencies]`, never dev-only.

### Tests use the same DB as production

Phase 2 gate must pass using PostgreSQL — not SQLite. `conftest.py` creates and tears down the test DB automatically.

### Phase 2 must pass with no API key

`APPNAME_LLM_PROVIDER=stub` must be set by default. The stub runs offline. Phase 2 gate fails if it requires a real API key.
