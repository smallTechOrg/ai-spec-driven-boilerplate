# Tech Stack — Email Triage Agent

## Language
Python 3.12

## Agent Framework
LangGraph — 3-node pipeline with per-email parallel classification

## LLM
Anthropic Claude (claude-haiku-4-5-20251001) — fast + cheap for classification

## Database
SQLite via SQLAlchemy 2.0 async + aiosqlite

## Key Libraries
| Library | Purpose |
|---------|---------|
| `anthropic` | Claude API |
| `google-api-python-client` | Gmail API |
| `google-auth-oauthlib` | OAuth |
| `langgraph` | Agent pipeline |
| `sqlalchemy[asyncio]` | ORM |
| `aiosqlite` | SQLite async driver |
| `pydantic` + `pydantic-settings` | Models + config |
| `pytest` + `pytest-asyncio` | Testing |

## Dependency Management
uv + pyproject.toml

## Phase Gate Commands
| Phase | Gate command |
|-------|-------------|
| 1 | `pytest tests/unit/` |
| 2 | `pytest tests/integration/` |
