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

<!-- FILL IN: Filled in by tech-designer based on language choice. -->

## File Organization

<!-- FILL IN: Filled in by tech-designer. How are files grouped — by layer, by feature, by type? -->

## Error Handling Pattern

<!-- FILL IN: Filled in by tech-designer. How are errors represented and propagated? -->

## Logging Pattern

<!-- FILL IN: Filled in by tech-designer. Structured vs. unstructured? What fields are always included? -->

## Testing Conventions

<!-- FILL IN: Filled in by tech-designer. Unit test location, naming, runner. -->

## What NOT to Do

<!-- FILL IN: Anti-patterns specific to this tech stack. Filled in by tech-designer. -->

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
