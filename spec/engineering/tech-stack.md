# Tech Stack

## Language: Python 3.12
## Database: PostgreSQL via SQLAlchemy 2.0 async + asyncpg
## Scheduler: APScheduler (future) — v0.1 is CLI-triggered
## Key Libraries: httpx, sqlalchemy[asyncio], asyncpg, aiosqlite (tests), pydantic-settings, pytest, pytest-asyncio
## Dependency Management: uv + pyproject.toml

## Phase Gate Commands
| Phase | Gate command |
|-------|-------------|
| 1 | `pytest tests/unit/` |
| 2 | `pytest tests/integration/` |
