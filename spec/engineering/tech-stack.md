# Tech Stack

## Language

**Python 3.12**

**Why:** User-specified. Best ecosystem for data manipulation (pandas) and AI/LLM libraries.

## Agent Framework

**LangGraph 0.2+**

**Why:** Structured state machine for the CSV-parse → analyze → finalize pipeline. Makes error routing explicit.

## LLM Provider

**Google Gemini via `google-genai` SDK**

**Model:** `gemini-2.5-flash`

**Why:** User has a Gemini API key. `gemini-2.5-flash` is the current recommended default for Gemini as of 2026.

## Backend Framework

**FastAPI 0.115+** with **uvicorn** and **Jinja2** templates

## Database

**SQLite** via **SQLAlchemy 2.0** (sync, declarative Mapped types)

**ORM/ODM:** SQLAlchemy 2.0 + Alembic for migrations

## Frontend

**Jinja2 templates** served by FastAPI. Minimal inline CSS. No JS framework in v0.1.

React/Vite frontend deferred to Phase 4.

## Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| fastapi | ≥0.115 | HTTP framework |
| uvicorn | ≥0.29 | ASGI server |
| jinja2 | ≥3.1 | HTML templates |
| python-multipart | ≥0.0.9 | File upload parsing |
| sqlalchemy | ≥2.0 | ORM + SQLite driver |
| alembic | ≥1.13 | Schema migrations |
| pydantic-settings | ≥2.2 | Settings from env |
| langgraph | ≥0.2 | Agent graph |
| google-genai | ≥1.0 | Gemini SDK |
| pandas | ≥2.2 | CSV parsing and analysis |
| structlog | ≥24 | Structured logging |

## What to Avoid

- PostgreSQL — user chose SQLite; do not introduce psycopg2
- Async SQLAlchemy — use sync engine; simpler with SQLite
- OpenAI SDK — Gemini only
- `alembic revision --autogenerate` before `script.py.mako` exists — it will fail

## Dependency Management

**uv** + `pyproject.toml`. All commands in docs use `uv run` prefix.

---

## Permanent Rules (apply to all projects, not filled in by tech-designer)

### Default Dev Port

All generated projects **must** use **port 8001** as the default development port (not 8000).

- `__main__.py` must hard-code `port=8001` (not 8000) unless overridden by an env var
- README must reference `http://localhost:8001`

### LLM Model Name Rule

**Always use a current, verified model name.**

- Gemini default: `gemini-2.5-flash`
- Configurable via `DATAANALYSIS_LLM_MODEL` env var

### DB Driver Rule

SQLite driver (`sqlite3`) is part of the Python standard library — no extra package needed. `aiosqlite` is NOT used (sync only).

### Test Environment Rule

Tests use SQLite (same as production). `conftest.py` creates a fresh in-memory or tmp-path database for each test session.
