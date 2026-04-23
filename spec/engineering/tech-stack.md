# Tech Stack — BlogForge

## Language

**Python 3.12**

Why: Strong ecosystem for LLM integrations, async support, LangGraph is Python-native, and the team has Gemini API access via the `google-generativeai` SDK.

## Agent Framework

**LangGraph**

Why: The generation pipeline has 4 sequential nodes (topic discovery → writer assignment → post generation → image generation) with state that flows through. LangGraph's StateGraph with a linear topology handles this cleanly and gives checkpointing for free. Site rendering is a future phase and is not part of the initial LangGraph graph.

## LLM Provider

**Google Gemini** — `gemini-2.0-flash` (text generation)

**Google Imagen** — `imagen-3.0-generate-002` (image generation)

Both accessed via `google-generativeai` SDK. This is the only LLM/image provider in use (per operator constraint).

## Backend Framework

**FastAPI** — serves the dashboard UI and REST API.

**Uvicorn** — ASGI server.

## Database

**SQLite** via SQLAlchemy 2.0 ORM + Alembic migrations.

Why: No separate database process; single file; easy to back up; appropriate for single-user deployment with low write volume.

## Scheduler

**APScheduler** (AsyncIOScheduler) — embedded in the FastAPI process.

## Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `google-generativeai` | latest | Gemini text + Imagen API client |
| `langgraph` | latest | Agent pipeline orchestration |
| `fastapi` | latest | REST API + dashboard server |
| `uvicorn` | latest | ASGI server |
| `sqlalchemy` | 2.x | ORM |
| `alembic` | latest | DB migrations |
| `apscheduler` | 3.x | Cron scheduling |
| `markdown` | latest | Markdown → HTML rendering (for dashboard display) |
| `croniter` | latest | Cron expression validation |
| `pydantic` | 2.x | Domain models + API validation |
| `duckduckgo-search` | latest | DuckDuckGo search (free, no API key) |
| `tavily-python` | latest | Tavily search API client |
| `aiofiles` | latest | Async file I/O (cover image writes must be non-blocking) |
| `httpx` | latest | Async HTTP calls |
| `pytest` | latest | Testing |
| `pytest-asyncio` | latest | Async test support |

**SVG placeholder generation:** No library needed. Placeholder SVGs are written as hardcoded string templates (a simple gradient rectangle) — no external dependency required.

## Dependency Management

`uv` + `pyproject.toml`

## Entry Point

The package exposes a CLI entry point via `pyproject.toml`:

```toml
[project.scripts]
blogforge = "blogforge.__main__:main"
```

This allows `python -m blogforge serve` to start the server. `src/blogforge/__main__.py` is the entry point; `src/blogforge/main.py` is the app factory.

## What to Avoid

- No OpenAI, Anthropic, or other LLM providers (operator has Gemini access only)
- No JavaScript frameworks in the dashboard (vanilla JS + HTML only — no npm, no build step)
- No external message queues or task runners (APScheduler embedded is sufficient)
- No Docker requirement (must run with `python -m blogforge serve` or `blogforge serve`)
- No synchronous file I/O in async handlers — use `aiofiles` for all disk writes
