import os
import tempfile

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.db.models  # noqa: F401  (register tables on Base.metadata before create_all)
import src.db.session as _session_module
from src.config import get_settings
from src.db.base import Base


@pytest.fixture(autouse=True)
def _offline_kill_switch():
    """Force the LLM into stub mode and point the DuckDB seam at a temp dir.

    Guarantees the suite never calls a network API and never writes a stray
    events.duckdb into the repo. SQLite is the production driver, so the db_session
    fixture below exercises the real async engine on the real driver.
    """
    os.environ["APPNAME_LLM_PROVIDER"] = "stub"
    os.environ["APPNAME_DATA_DIR"] = tempfile.mkdtemp(prefix="appname_test_")
    get_settings.cache_clear()
    assert get_settings().resolved_llm_provider == "stub"
    yield
    get_settings.cache_clear()


@pytest.fixture
async def db_session(monkeypatch, tmp_path) -> AsyncSession:
    """A fresh, throwaway SQLite DB per test via the real async engine.

    Yields a session bound to that DB and swaps the app's ``AsyncSessionLocal`` so
    request handlers use the same store.
    """
    db_url = f"sqlite+aiosqlite:///{tmp_path}/appname_test.db"
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(_session_module, "AsyncSessionLocal", factory)

    async def _noop():
        pass

    monkeypatch.setattr(_session_module, "init_db", _noop)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
