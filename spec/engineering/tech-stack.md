# Tech Stack

> **Boilerplate status:** Filled in by the tech-designer sub-agent after the product spec is approved. The user may override specific choices before the tech-designer is invoked.

---

## Language

<!-- FILL IN: e.g., Python 3.12 / TypeScript 5 / Go 1.22 -->

**Why:** <!-- reason for this choice -->

## Agent Framework

<!-- FILL IN: e.g., LangGraph / CrewAI / AutoGen / custom / none -->

**Why:** <!-- reason for this choice -->

## LLM Provider

<!-- FILL IN: e.g., Anthropic Claude / OpenAI GPT / Google Gemini -->

**Model:** <!-- specific model, e.g., claude-sonnet-4-6 -->

**Why:** <!-- reason -->

## Backend Framework (if applicable)

<!-- FILL IN: e.g., FastAPI / Express / Django / none -->

## Database (if applicable)

<!-- FILL IN: e.g., PostgreSQL / SQLite / Redis / none -->

**ORM/ODM:** <!-- e.g., SQLAlchemy 2.0 / Prisma / none -->

## Frontend (if applicable)

<!-- FILL IN: e.g., Next.js 15 / React / Vue / none -->

## Key Libraries

<!-- FILL IN: List the important libraries and what each does. -->

| Library | Version | Purpose |
|---------|---------|---------|
| <!-- name --> | <!-- version --> | <!-- purpose --> |

## What to Avoid

<!-- FILL IN: Libraries, patterns, or approaches that are explicitly off-limits and why. -->

## Dependency Management

<!-- FILL IN: e.g., uv + pyproject.toml / npm / pnpm / go modules -->

---

## Permanent Rules (apply to all projects, not filled in by tech-designer)

### Default Dev Port

All generated projects **must** use **port 8001** as the default development port (not 8000).

Reason: Port 8000 is commonly occupied by other local services (other FastAPI apps, Django, http.server, etc.). Using 8001 avoids startup failures with no code change needed.

- `__main__.py` must hard-code `port=8001` (not 8000) unless overridden by an env var
- README must reference `http://localhost:8001`
- `.env.example` should include `PORT=8001` if the port is configurable

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
