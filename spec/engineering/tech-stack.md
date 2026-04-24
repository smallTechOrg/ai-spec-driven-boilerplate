# Tech Stack

## Language

Python 3.12

**Why:** Matches the rest of the operator's toolchain, LangGraph/SQLAlchemy/pydantic all first-class.

## Agent Framework

LangGraph

**Why:** Linear pipeline with explicit error short-circuit fits StateGraph cleanly; required by repo's 07-agent-graph.md rule.

## LLM Provider

Google Gemini via `google-genai`. Provider selection: `auto` (real when `GEMINI_API_KEY` set, stub otherwise).

**Model:** `gemini-2.5-flash` (configurable via `LEADGEN_LLM_MODEL`).

**Why:** Cost-effective for short extract/score prompts; matches repo's LLM-model-name rule.

## Backend Framework

FastAPI (Starlette ≥1.0 — use the new `TemplateResponse(request, name, ctx)` signature).

## Database

PostgreSQL via SQLAlchemy 2.0 sync + psycopg2. Alembic for migrations. Tests hit Postgres — never SQLite (per repo rule 5).

**ORM:** SQLAlchemy 2.0 declarative (`Mapped[...]`).

## Frontend

Server-rendered Jinja2 templates. No client framework.

## Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| fastapi | ≥0.115 | Web framework |
| jinja2 | ≥3.1 | Templates |
| sqlalchemy | ≥2.0 | ORM |
| psycopg2-binary | ≥2.9 | Postgres driver (main deps — never dev-only) |
| alembic | ≥1.13 | Migrations |
| langgraph | ≥0.2 | Agent orchestration |
| google-genai | ≥0.3 | Gemini client |
| pydantic-settings | ≥2.4 | Config with `extra="ignore"` |
| httpx + beautifulsoup4 | current | DuckDuckGo HTML scraping |
| structlog | ≥24 | Logs |

## What to Avoid

- SQLite for any tests (rule 5)
- `TemplateResponse("page.html", {"request": ...})` — the pre-1.0 signature; use new signature
- Calling Gemini SDK directly from nodes — always go through `LLMClient`
- Keyword-matching in stub LLM (rule 8) — branch on `<node:*>` tags only

## Dependency Management

`uv` + `pyproject.toml`. All commands prefixed with `uv run`.

---

## Permanent Rules (apply to all projects, not filled in by tech-designer)

### Default Dev Port

All generated projects **must** use **port 8001** as the default development port (not 8000).

Reason: Port 8000 is commonly occupied by other local services (other FastAPI apps, Django, http.server, etc.). Using 8001 avoids startup failures with no code change needed.

- `__main__.py` must hard-code `port=8001` (not 8000) unless overridden by an env var
- README must reference `http://localhost:8001`
- `.env.example` should include `PORT=8001` if the port is configurable

### LLM Model Name Rule

**Always use a current, verified model name — never a deprecated or guessed one.**

- For Google Gemini: use **`gemini-2.0-flash`** as the default (not `gemini-1.5-flash` — deprecated and removed from the API).
- Model names change. Before hardcoding any model identifier, verify it exists by calling the provider's `ListModels` API or checking current documentation.
- The model name must be configurable via an env var (e.g. `APPNAME_LLM_MODEL`) so it can be changed without a code deployment.
- A 404 NOT_FOUND error from the LLM API almost always means the model name is wrong — check the name first before debugging anything else.

Current safe defaults (as of 2026):

| Provider | Default model | Notes |
|----------|---------------|-------|
| Google Gemini | `gemini-2.5-flash` | `gemini-2.0-flash` and `gemini-1.5-flash` unavailable for new users |
| OpenAI | `gpt-4o-mini` | |
| Anthropic | `claude-3-5-haiku-latest` | |

### DB Driver Rule

The database driver (e.g. `psycopg2-binary` for PostgreSQL, `asyncpg` for async PostgreSQL) **must be declared in the main `[project.dependencies]` block**, never in `[dependency-groups.dev]` or equivalent dev-only groups.

Reason: Alembic migrations run at deploy/setup time, not just in tests. If the driver is dev-only, `alembic upgrade head` fails in any environment that didn't install dev deps.

### Test Environment Rule

**Tests must use the same database driver as production.** If the production DB is PostgreSQL, tests run against PostgreSQL — not SQLite.

- Tests that pass on SQLite but were never run against PostgreSQL are **not a passing gate**.
- The test database must be set up automatically. Use `conftest.py` to create and tear down the test database. No manual steps.
- The test database URL is provided via environment variable (e.g. `TEST_DATABASE_URL` or reuse the app's `DATABASE_URL` pointing at a `_test` database). The `conftest.py` session fixture creates all tables before tests run and drops them after.
- A `.env.test` file (gitignored) or CI environment variable provides the test DB URL. The README must document this.

Example `conftest.py` pattern for PostgreSQL + SQLAlchemy (sync):

```python
import pytest
from sqlalchemy import create_engine, text
from yourapp.db.models import Base
from yourapp.config.settings import get_settings

@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
```

The `DATABASE_URL` in `.env` (or `.env.test`) must point at a real PostgreSQL test database before running tests.
