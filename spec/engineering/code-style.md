# Code Style — BlogForge

## Universal Rules (always apply)

- Types at every boundary — Pydantic models for all domain objects; no raw dicts crossing module lines
- One responsibility per file — if a file does two things, split it
- No comments explaining WHAT — names do that; only comment WHY for non-obvious decisions
- No dead code — no commented-out code, no unused imports
- Fail loudly at startup — validate all env vars and DB connection before accepting requests

## Python-Specific

- **Style:** PEP 8; line length 100
- **Types:** Full type annotations on all function signatures; `mypy --strict` must pass
- **Async:** Use `async/await` throughout (FastAPI + APScheduler + Gemini async calls)
- **Imports:** Standard lib → third-party → local, separated by blank lines; absolute imports only

## Naming Conventions

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions / variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Pydantic domain models: suffix with no special marker (e.g. `Post`, `Writer`, `Blog`)
- SQLAlchemy ORM models: prefix with `DB` (e.g. `DBPost`, `DBWriter`) to distinguish from domain models

## File Organization

```
src/blogforge/
  api/            ← FastAPI routers (one file per resource: blog.py, writers.py, runs.py, posts.py)
  agent/          ← LangGraph graph (state.py, nodes.py, edges.py, graph.py, runner.py)
  tools/          ← Pure tool functions (one file per tool)
  domain/         ← Pydantic domain models (models.py)
  db/             ← SQLAlchemy models + session (models.py, session.py)
  dashboard/      ← index.html (single-file dashboard)
  scheduler.py    ← APScheduler setup
  config.py       ← Pydantic settings (env vars)
  main.py         ← App factory (FastAPI app + scheduler startup)
tests/
  unit/           ← Unit tests per module
  integration/    ← Full pipeline tests
```

## Error Handling Pattern

- External calls (Gemini, Google Trends): wrap in `try/except`, log the error, return a typed failure result
- Never let an exception in one post's generation crash the entire run — catch at the node level
- Use Python's `logging` module with structured fields: `logger.error("msg", extra={"post_id": ..., "run_id": ...})`
- Errors are persisted to `Run.error_message` (for run-level failures) or logged (for post-level failures)

## Logging Pattern

- Use Python's standard `logging` module
- Every log line includes at minimum: `run_id` (if in a run), the operation name
- Log levels: DEBUG for LLM prompts/responses, INFO for node transitions and completions, WARNING for fallbacks (e.g. image placeholder), ERROR for failures

## Testing Conventions

- Test files mirror source: `tests/unit/test_tools_topic_discovery.py` for `src/blogforge/tools/topic_discovery.py`
- Test function names: `test_[what]_[condition]_[expected]` e.g. `test_topic_discovery_no_trending_returns_niche_topics`
- Run all tests: `pytest`
- External API calls must be mocked in unit tests; only integration tests call real APIs
- Each phase's tests must pass before writing phase N+1 code

## What NOT to Do

- No raw `dict` passing between modules — use Pydantic models
- No `time.sleep()` in async code — use `asyncio.sleep()`
- No synchronous DB calls in async route handlers — use `async with` session
- No hardcoded API endpoints or model names — all in `config.py`
- No print statements — use `logging`
