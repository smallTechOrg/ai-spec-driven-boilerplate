# Tech Stack

## Language
Python 3.12.
**Why:** user preference; LangGraph ecosystem.

## Agent Framework
LangGraph.
**Why:** user preference.

## LLM Provider
Google Gemini. **Model:** `gemini-2.5-flash` (current safe default).
**Why:** user preference; free tier.

## Backend Framework
FastAPI + Jinja2 templates.

## Database
PostgreSQL 15+. **ORM:** SQLAlchemy 2.0 (sync). **Migrations:** Alembic.

## Frontend
None — server-rendered HTML via Jinja2.

## Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| fastapi | ^0.115 | HTTP + routing |
| uvicorn | ^0.32 | ASGI server |
| jinja2 | ^3.1 | Templates |
| python-multipart | ^0.0.17 | Form parsing |
| sqlalchemy | ^2.0 | ORM |
| psycopg2-binary | ^2.9 | PG driver (prod + tests) |
| alembic | ^1.13 | Migrations |
| pydantic | ^2.9 | Domain models |
| pydantic-settings | ^2.6 | Config |
| langgraph | ^0.2 | Agent state machine |
| google-generativeai | ^0.8 | Gemini SDK |
| markdown | ^3.7 | Render article body |
| structlog | ^24 | Logging |
| pytest | ^8 | Tests |
| httpx | ^0.27 | TestClient |

## What to Avoid

- SQLite for tests (Postgres only)
- Async SQLAlchemy (sync is enough for v0.1)
- Heavy frontend frameworks

## Dependency Management
`uv` + `pyproject.toml`.

---

## Permanent Rules (apply to all projects)

### Default Dev Port
Port **8001** (not 8000) — avoids conflicts. `__main__.py` hard-codes 8001; README references `http://localhost:8001`.

### LLM Model Name Rule
- Gemini default: **`gemini-2.5-flash`** (2.0 / 1.5 unavailable for new users).
- Model name must be configurable via env var (`BLOGFORGE_LLM_MODEL`).
- A 404 from the LLM API almost always means the model name is wrong.

### DB Driver Rule
`psycopg2-binary` lives in `[project.dependencies]`, never in dev-only groups. Alembic runs at deploy time.

### Test Environment Rule
Tests run against PostgreSQL, same driver as production. `conftest.py` creates/drops schema automatically.

