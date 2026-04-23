# Standard Project Layout

Every agent built with this boilerplate follows this layout. The agent-builder uses it as the template for Phase 1 and Phase 2 file lists.

## Python Projects

```
src/{package}/
  __init__.py
  __main__.py          # entry point: asyncio.run(run_agent())
  config.py            # pydantic-settings Settings class
  domain/
    __init__.py
    models.py          # Pydantic domain models (not ORM)
  db/
    __init__.py
    models.py          # SQLAlchemy ORM models (Base, DB* classes)
    session.py         # engine, AsyncSessionLocal, get_session(), init_db()
    repository.py      # async CRUD functions — return domain models, not ORM rows
  agent/
    __init__.py
    state.py           # TypedDict state (if using LangGraph)
    nodes.py           # one async function per node
    graph.py           # build_graph() + graph = build_graph().compile()
    runner.py          # run_agent() — calls init_db, creates run, invokes graph
  tools/
    __init__.py
    {integration}.py   # one file per external system (github.py, slack.py, etc.)

tests/
  __init__.py
  conftest.py          # db_session fixture using tmp_path SQLite
  unit/
    __init__.py
    db/
      __init__.py
      test_repository.py
  integration/
    __init__.py
    test_pipeline.py   # end-to-end: run_agent() → assert DB state
```

## Stub Shapes (Phase 2)

Every tool file in Phase 2 must be a stub that returns hardcoded data:

```python
# tools/github.py — Phase 2 stub
STUB_RESULTS = [...]   # hardcoded list

async def fetch_data(param: str) -> list[Thing]:
    """Stub: returns hardcoded data. Replace in Phase 3."""
    return STUB_RESULTS
```

The Phase 2 integration test fixture pattern (copy this exactly):

```python
@pytest.fixture(autouse=True)
async def _use_test_db(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    import {package}.db.session as s
    monkeypatch.setattr(s, "AsyncSessionLocal", factory)
    monkeypatch.setattr(s, "engine", engine)

    async def _noop(): pass
    monkeypatch.setattr("{package}.agent.runner.init_db", _noop)
    yield
    await engine.dispose()
```

## session.py Standard Shape

```python
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def init_db() -> None:
    from {package}.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

`engine` and `AsyncSessionLocal` are module-level so integration tests can monkeypatch them.

## conftest.py Standard Shape

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from {package}.db.models import Base

@pytest.fixture
async def db_session(tmp_path) -> AsyncSession:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
```

Use `tmp_path` not `:memory:` — avoids shared-state issues across tests.
