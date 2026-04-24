# Code Style

> **Boilerplate status:** The tech-designer sub-agent fills in the language-specific sections. General rules below apply to all projects.

---

## Universal Rules

These apply regardless of language or framework:

1. **Types at boundaries** — every function that crosses a module boundary must use typed inputs and outputs (Pydantic, TypeScript interfaces, Go structs, etc.) — never raw dicts or `any`
2. **One responsibility per file** — a file does one thing; if it's doing two things, split it
3. **No comments explaining WHAT** — code should be self-documenting via names; only comment WHY something non-obvious is done
4. **No dead code** — remove unused imports, functions, and variables immediately; don't comment them out
5. **Fail loudly at startup** — validate all required config/env vars at startup; don't fail silently at runtime
6. **No hardcoding** — values that could change (URLs, limits, credentials) go in config or environment variables

## Naming Conventions

- Modules & files: snake_case (`search_node.py`). Package: `lead_gen_agent`.
- Classes: PascalCase (`SearchTool`, `LeadRow`). Functions/vars: snake_case.
- Env vars: `LEADGEN_*` (plus `GEMINI_API_KEY`, `PORT`).
- DB rows: `*Row` (`RunRow`, `LeadRow`). Pydantic domain models: plain noun (`Run`, `Lead`).

## File Organization

Grouped by layer: `config/`, `db/`, `domain/`, `graph/`, `llm/`, `tools/`, `api/`. Templates under `api/templates/`; static assets under `api/static/`. Tests mirror the source tree under `tests/unit/` and `tests/integration/`.

## Error Handling Pattern

- Graph nodes set `state["error"]` on failure; they never raise. `persist_node` consults `state["error"]` and marks the run `failed`.
- Web routes catch no exceptions directly; unhandled errors render `error.html` via a global exception handler.
- Tool calls (search/LLM) catch their own network errors, log, and degrade gracefully (empty list / default score).

## Logging Pattern

`structlog` with `log_level` from settings. Every major op emits one event: `search.started`, `search.completed`, `extract.completed`, `score.completed`, `persist.completed`, `run.failed`. Include `run_id` on every event.

## Testing Conventions

- Runner: `uv run pytest`. Config in `pyproject.toml` (`testpaths = ["tests"]`).
- Unit tests mirror module path: `tests/unit/db/test_repository.py`.
- Integration tests under `tests/integration/`; the golden-path UI smoke lives there.
- Tests hit the real `lead_gen_agent_test` Postgres DB — never SQLite.

## What NOT to Do

- Don't call `google.genai` directly outside `llm/providers/`.
- Don't build raw SQL strings — use SQLAlchemy.
- Don't put business logic in templates.
- Don't use the pre-1.0 Starlette `TemplateResponse` signature.
- Don't keyword-match in the stub — branch on `<node:*>` tags only.

---

## Test Environment Rules

These apply to all projects. No exceptions.

1. **Same DB as production** — if the app uses PostgreSQL, tests use PostgreSQL. SQLite is not a substitute. A test suite that only passes on SQLite tells you nothing about whether migrations and queries work against the real database.

2. **Automated setup — no manual steps** — the `conftest.py` (or equivalent test setup) must create all required tables and tear them down automatically. The test runner must work with a single command (`uv run pytest`, `bun test`, etc.) after setting the test DB URL.

3. **Isolated test database** — use a dedicated database (e.g. `myapp_test`, not `myapp`). Never run tests against the development or production database.

4. **Test DB URL via environment** — expose the test database URL through the same env var mechanism as the app (e.g. `DATABASE_URL` pointing at the test DB, or a `TEST_DATABASE_URL` that the conftest reads). Document this in the README.

5. **DB URL in `.env.example`** — the `.env.example` file must include the test DB URL with a clear placeholder so a new developer knows what to fill in.

6. **`alembic upgrade head` in CI / README** — the README must include `alembic upgrade head` as an explicit step before running the app or tests. Never rely on auto-create from SQLAlchemy metadata alone in production.

---

## Framework Gotchas (keep up to date — known footguns)

### Starlette ≥ 1.0 `TemplateResponse` signature

Starlette 1.0 and FastAPI 0.115+ require the **new** `TemplateResponse` call signature:

```python
# CORRECT (Starlette ≥ 1.0)
return templates.TemplateResponse(request, "page.html", {"foo": bar})

# WRONG (pre-1.0 form) — fails with TypeError: unhashable type: 'dict'
return templates.TemplateResponse("page.html", {"request": request, "foo": bar})
```

A small helper in the routes module keeps call sites tidy:

```python
def render(request: Request, name: str, **ctx):
    return templates.TemplateResponse(request, name, ctx)
```

### LLM provider selection and stubs

Any project with an LLM dependency must follow these patterns:

1. **`provider=auto` by default.** Resolve to the real provider when the API key env var is set, otherwise to the stub. Setting the key is the only step the user should need. Add a `resolved_llm_provider` property on `Settings` that encapsulates this.

2. **Stub outputs branch on explicit node tags, not prose keywords.** Each pipeline node injects a unique tag (`<node:plan>`, `<node:draft>`, `<node:title>`, ...) into its prompt, and the stub matches those tags. Matching on words that also appear in the prompt body cross-contaminates — a draft prompt that contains "expand this outline" must never trigger the stub's "outline" branch.

3. **Stub "draft"-class outputs are article-shaped.** Multiple paragraphs and/or headings — not a bare bullet list. Offline demos must be believable.

4. **The UI shows a visible stub-mode banner** on every page when the resolved provider is `stub`. Inject `llm_provider` into every template context. Silent stubs are a bug.

5. **Tolerate dirty `.env` values.** Config resolution must strip inline `#` comments and surrounding whitespace before comparing enum-like env values (`provider`, `mode`, etc.). A `.env` written months ago with `BLOGFORGE_LLM_PROVIDER=stub   # stub | gemini` must not silently pin the wrong provider. Pydantic-settings does NOT strip inline comments — do it yourself in a `resolved_*` property, never trust the raw field.

---

## Integration Test Patterns

### Replacing an async init function in tests

When your runner calls an async `init_db()` or similar startup function, monkeypatch it with an async noop — not a sync lambda:

```python
# CORRECT
async def _noop(): pass
monkeypatch.setattr("mypackage.agent.runner.init_db", _noop)

# WRONG — breaks await
monkeypatch.setattr("mypackage.agent.runner.init_db", lambda: None)
```

### Replacing the DB session factory in integration tests

```python
@pytest.fixture(autouse=True)
async def _use_test_db(monkeypatch, tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    import mypackage.db.session as s
    monkeypatch.setattr(s, "AsyncSessionLocal", factory)
    monkeypatch.setattr(s, "engine", engine)

    async def _noop(): pass
    monkeypatch.setattr("mypackage.agent.runner.init_db", _noop)
    yield
    await engine.dispose()
```

Use `tmp_path` (not `:memory:`) for integration tests — it avoids shared-state issues across tests.

---

## Pydantic-settings — Always Set `extra="ignore"`

`pydantic-settings` reads **the entire `.env` file** and passes every key to Pydantic for validation. If the `.env` file contains variables the `Settings` model doesn't declare (e.g. `TEST_DATABASE_URL`, `EDITOR`, CI vars), Pydantic will raise:

```
ValidationError: Extra inputs are not permitted [type=extra_forbidden]
```

**Fix:** always set `extra="ignore"` in the `model_config`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APPNAME_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # ← required — .env may contain vars we don't own
    )
```

This is mandatory for any project whose `.env` contains variables owned by other tools (test runners, editors, CI, Docker, etc.).

---

## Pipeline Errors — Render an Error Template, Never Raise HTTPException

When an LLM pipeline node fails (provider 4xx/5xx, invalid response, timeout), the failure propagates back to the route via the pipeline state's `error` field.

**Do not** re-raise this as an `HTTPException`:

```python
# WRONG — returns a bare JSON error body to the browser with a 422 status
if state["error"]:
    raise HTTPException(status_code=422, detail=state["error"])
```

**Do** render the error template instead:

```python
# CORRECT — shows the user a readable error page with a "Try again" link
if state["error"]:
    log.error("analyze.pipeline_error", error=state["error"])
    return render(request, "error.html", detail=state["error"])
```

The `error.html` template must always exist and must include a link back to the upload/start page.
Every web route that calls `run_pipeline()` (or equivalent) must follow this pattern.
