# Architecture

## System Overview

Single-process Python app. FastAPI serves Jinja2-rendered HTML pages for CRUD on Voices/Writers and article generation. A LangGraph state machine runs in-process to produce articles via Gemini.

## Component Map

```
[Browser]
    ↓ HTTP
[FastAPI + Jinja2 UI]
    ↓
[Repository (SQLAlchemy)]   →   [PostgreSQL]
    ↓
[LangGraph Runner]
    ↓
[LLM Client (Gemini)]       →   [Google Gemini API]
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| `api/` | FastAPI routes, Jinja2 templates, form handling |
| `graph/` | LangGraph state machine (plan → draft → finalize) |
| `llm/` | Gemini provider + stub provider for tests |
| `db/` | SQLAlchemy models, session factory |
| `domain/` | Pydantic models (boundary types) |
| `config/` | Settings (Pydantic BaseSettings) |

## Data Flow

1. User opens `/`, creates a Voice, then a Writer linked to that Voice
2. User opens `/articles/new`, picks writer + types topic, submits
3. FastAPI route creates an `AgentRun` row, invokes LangGraph runner
4. Runner loads writer + voice, runs plan → draft → finalize nodes
5. Final article saved; user is redirected to the article page

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| PostgreSQL | Persistence | App won't start |
| Google Gemini API | Article generation | Article creation returns error; existing articles still viewable |

## Deployment Model

Local `uv run python -m blogforge` → FastAPI on `http://localhost:8001`.
