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
- Pydantic domain models: no special suffix (e.g. `Post`, `Writer`, `Blog`)
- SQLAlchemy ORM models: prefix with `DB` (e.g. `DBPost`, `DBWriter`) to distinguish from domain models

## File Organization

```
src/blogforge/
  __main__.py     ← Entry point (python -m blogforge serve)
  main.py         ← App factory (FastAPI app + scheduler startup)
  config.py       ← Pydantic settings (env vars)
  scheduler.py    ← APScheduler setup
  api/            ← FastAPI routers (blog.py, writers.py, runs.py, posts.py)
  agent/          ← LangGraph graph (state.py, nodes.py, graph.py, runner.py)
  tools/          ← Pure tool functions (one file per tool)
  domain/         ← Pydantic domain models (models.py)
  db/             ← SQLAlchemy ORM models + session (models.py, session.py)
  dashboard/      ← index.html (single-file dashboard, self-contained)
tests/
  conftest.py     ← Shared fixtures: in-memory SQLite DB, mocked Gemini client, tmp image dir
  unit/           ← Unit tests per module (mirror src/ structure)
  integration/    ← Full pipeline tests (call real DB, mock external APIs)
```

## Async File I/O

All disk writes (cover images, SVG placeholders) must use `aiofiles` — never `open()` in an async context:

```python
# Correct
import aiofiles
async def save_image(path: Path, data: bytes) -> None:
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)

# Wrong — blocks the event loop
def save_image(path: Path, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)
```

## SVG Placeholder Generation

When Gemini Imagen fails, write a hardcoded SVG placeholder (no library needed):

```python
SVG_PLACEHOLDER = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#1a1a2e"/>
    <stop offset="100%" stop-color="#16213e"/>
  </linearGradient></defs>
  <rect width="1200" height="630" fill="url(#g)"/>
</svg>"""
```

Write it via `aiofiles` with `.svg` extension. The `cover_image_path` field in the Post record uses the `.svg` extension so the dashboard renders it correctly.

## Error Handling Pattern

- External calls (Gemini, DuckDuckGo, Tavily): wrap in `try/except`, log the error, return a typed failure result
- A "failure" for search APIs means: `httpx.TimeoutException`, `httpx.HTTPStatusError` (4xx/5xx), or any exception from the client library
- Never let an exception in one post's generation crash the entire run — catch at the node level, mark that post as failed, continue
- Errors logged with structured extra fields:

```python
logger.error("gemini_text_failed", extra={"run_id": run_id, "post_topic": topic, "error": str(e)})
```

- Run-level fatal errors persisted to `Run.error_message`; post-level failures logged only

## Logging Pattern

- Standard `logging` module (no third-party logging library)
- Every log line includes at minimum: `run_id` (if in a run context), the operation name
- Log levels:
  - `DEBUG` — LLM prompts/responses (verbose; off by default in production)
  - `INFO` — node transitions, completions, run start/end
  - `WARNING` — fallbacks activated (e.g. SVG placeholder used, one search source skipped)
  - `ERROR` — failures that affect output (post failed, run failed)

## Testing Conventions

- Test files mirror source structure: `tests/unit/tools/test_topic_discovery.py` for `src/blogforge/tools/topic_discovery.py`
- Naming: `test_[what]_[condition]_[expected]` — e.g. `test_topic_discovery_both_search_fail_returns_llm_only`
- Run all tests: `pytest`
- `conftest.py` provides: in-memory SQLite session, mocked `google-generativeai` client, temporary image directory
- External API calls mocked in all unit tests; integration tests use real SQLite but still mock Gemini/search
- Phase gate: each phase's tests must pass before writing any phase N+1 code

## What NOT to Do

- No raw `dict` passing between modules — use Pydantic models
- No `time.sleep()` in async code — use `asyncio.sleep()`
- No synchronous DB calls in async route handlers — use `async with session`
- No synchronous file I/O in async handlers — use `aiofiles`
- No hardcoded API endpoints, model names, or config values — all in `config.py`
- No print statements — use `logging`
- No catching bare `Exception` without logging and re-raising or returning a typed error
