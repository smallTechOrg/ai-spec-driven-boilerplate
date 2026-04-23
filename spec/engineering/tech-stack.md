# Tech Stack — PR Staleness Monitor

## Language
Python 3.12

## Agent Framework
None — linear pipeline: fetch → filter → notify. No LangGraph needed.

## LLM
None — no LLM calls in v0.1. Pure API + logic.

## Database
PostgreSQL via SQLAlchemy 2.0 async + asyncpg + Alembic migrations.

## Scheduler
APScheduler (AsyncIOScheduler) — embedded in the process.

## Key Libraries

| Library | Purpose |
|---------|---------|
| `httpx` | Async GitHub API + Slack webhook calls |
| `sqlalchemy[asyncio]` | ORM |
| `asyncpg` | PostgreSQL async driver |
| `alembic` | DB migrations |
| `apscheduler` | Cron scheduling |
| `pydantic` | Domain models + config |
| `pydantic-settings` | Env var config |
| `pytest` + `pytest-asyncio` | Testing |

## Dependency Management
`uv` + `pyproject.toml`

## Entry Point
`python -m prmonitor run` — single cron-triggered run
`python -m prmonitor serve` — long-running with APScheduler
