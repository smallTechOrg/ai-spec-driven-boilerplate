# Implementation Plan — Food Tracker

## Minimal Working Thing (Phase 2 Goal)

By the end of Phase 2, the full web flow runs end-to-end without any API key: a user opens `http://localhost:8001`, uploads any image file, and sees a nutrition breakdown on screen (with a visible "DEMO MODE" banner). The stub provider returns deterministic hardcoded data. One `food_logs` row is written to PostgreSQL for each submission. All unit and integration tests pass with `uv run pytest`. The server starts cleanly with `uv run python -m food_tracker` and `/health` returns `{"status": "ok"}`.

---

## Phases

### Phase 1 — Domain Models + Data Layer

**Goal:** Define the `FoodLog` SQLAlchemy model, Pydantic domain types, Alembic migration, and basic CRUD unit tests. No HTTP layer, no LLM calls.

**Files to create/modify:**
- `pyproject.toml` — project metadata, all runtime deps (including `psycopg2-binary` as a production dep)
- `src/food_tracker/__init__.py` — `__version__ = "0.1.0"`
- `src/food_tracker/config/__init__.py`
- `src/food_tracker/config/settings.py` — `Settings(BaseSettings)` with all env vars, validated at startup
- `src/food_tracker/db/__init__.py`
- `src/food_tracker/db/models.py` — `FoodLog` SQLAlchemy 2.0 declarative model
- `src/food_tracker/db/session.py` — engine, sessionmaker, `get_session()` dependency
- `src/food_tracker/domain/__init__.py`
- `src/food_tracker/domain/food_log.py` — `NutritionResult`, `FoodLogCreate`, `FoodLogRead` Pydantic models
- `alembic.ini` — points at `alembic/` directory
- `alembic/env.py` — reads DB URL from settings; sets `target_metadata = Base.metadata`
- `alembic/script.py.mako` — standard mako template
- `alembic/versions/0001_initial.py` — initial migration (generated)
- `tests/__init__.py`
- `tests/conftest.py` — settings singleton reset; test DB session setup/teardown
- `tests/unit/__init__.py`
- `tests/unit/test_smoke.py` — `import food_tracker; assert __version__ == "0.1.0"`
- `tests/unit/config/test_settings.py` — settings validation
- `tests/unit/db/test_models.py` — FoodLog CRUD against test PostgreSQL
- `tests/unit/domain/test_models.py` — Pydantic model validation

**Gate:**
1. `uv run alembic upgrade head` succeeds against the test database
2. `uv run pytest tests/unit/` passes with 0 failures
3. Working tree committed

---

### Phase 2 — Web UI + Stubbed Pipeline

**Goal:** Add FastAPI routes, Jinja2 templates, the linear pipeline runner, stub LLM provider, and integration tests. Full end-to-end flow with zero real API calls.

**Files to create/modify:**
- `src/food_tracker/api/__init__.py` — `create_app()` factory with lifespan
- `src/food_tracker/api/_common.py` — `render()` helper (Starlette 1.0-compatible `TemplateResponse`)
- `src/food_tracker/api/food.py` — `GET /`, `POST /analyze`, `GET /health` routes
- `src/food_tracker/graph/__init__.py`
- `src/food_tracker/graph/state.py` — `FoodState(TypedDict)`
- `src/food_tracker/graph/nodes.py` — `node_analyse_food()`, `node_save_log()`
- `src/food_tracker/graph/runner.py` — `run_pipeline(image_bytes, image_filename, session) -> FoodState`
- `src/food_tracker/llm/__init__.py`
- `src/food_tracker/llm/providers/__init__.py`
- `src/food_tracker/llm/providers/base.py` — `LLMProvider` abstract class
- `src/food_tracker/llm/providers/stub.py` — `StubProvider` returning hardcoded `NutritionResult`
- `src/food_tracker/llm/providers/factory.py` — `create_provider()` → gemini if key present, else stub
- `src/food_tracker/observability/__init__.py`
- `src/food_tracker/observability/events.py` — structlog configuration
- `src/food_tracker/templates/base.html` — shared layout with stub banner slot
- `src/food_tracker/templates/upload.html` — file upload form
- `src/food_tracker/templates/result.html` — nutrition breakdown + stub banner
- `src/food_tracker/templates/error.html` — error page
- `src/food_tracker/__main__.py` — `uvicorn.run(port=8001)`
- `.env.example` — all env vars documented
- `.gitignore` — `.env`, `__pycache__`, `.venv`, `*.pyc`
- `README.md` — full setup instructions, all commands prefixed with `uv run`
- `tests/integration/__init__.py`
- `tests/integration/test_pipeline.py` — full POST /analyze with stub, asserts 1 DB row + HTML content

**Gate:**
1. `uv run pytest tests/` passes with 0 failures (PostgreSQL, stub mode, no API key needed)
2. Live-server smoke: `uv run python -m food_tracker &` → `curl http://localhost:8001/health` returns `{"status":"ok"}`; `curl http://localhost:8001/` returns HTML with "Food Tracker"
3. Stub banner visible in the POST /analyze response HTML
4. Working tree committed

---

### Phase 3 — Real Gemini Vision Integration

**Goal:** Implement the Gemini provider. When `FOOD_TRACKER_GEMINI_API_KEY` is set, real Gemini Vision is called instead of the stub.

**Files to create/modify:**
- `src/food_tracker/llm/providers/gemini.py` — `GeminiProvider` using `google-generativeai` SDK
- `src/food_tracker/prompts/food_analysis.md` — prompt template for Gemini
- `tests/integration/test_gemini_live.py` — optional live test (skipped unless `FOOD_TRACKER_GEMINI_API_KEY` is set)

**Gate:**
1. `FOOD_TRACKER_GEMINI_API_KEY=<key> uv run pytest tests/integration/test_gemini_live.py -v` passes — real food photo returns structured nutrition data
2. Working tree committed

---

## Deferred to Future Phases

- Micronutrient breakdown (Phase 4+)
- Daily totals / history dashboard (Phase 5+)
- User authentication (Phase 6+)
- Error retries and rate-limit handling (Phase 4+)
- Structured logging to a file/service (Phase 4+)
