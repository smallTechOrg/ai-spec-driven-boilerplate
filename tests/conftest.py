from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _test_db_url() -> str:
    url = os.environ.get("SOURCING_TEST_DATABASE_URL")
    if not url:
        url = "postgresql+psycopg2://localhost:5432/sourcing_test"
    return url


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Point the app at the test DB and reset cached singletons every test."""
    monkeypatch.setenv("SOURCING_DATABASE_URL", _test_db_url())
    monkeypatch.setenv("SOURCING_LLM_PROVIDER", "stub")
    monkeypatch.setenv("SOURCING_SEARCH_PROVIDER", "stub")
    monkeypatch.delenv("SOURCING_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SOURCING_TAVILY_API_KEY", raising=False)

    import sourcing_agent.config.settings as settings_mod
    import sourcing_agent.db.session as session_mod

    settings_mod._settings = None
    session_mod._engine = None
    session_mod._SessionLocal = None
    yield
    settings_mod._settings = None
    session_mod._engine = None
    session_mod._SessionLocal = None


@pytest.fixture(autouse=True)
def _schema(_env):
    """Create all tables in the test DB before each test, drop after."""
    from sourcing_agent.db.models import Base

    engine = create_engine(_test_db_url(), future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session():
    engine = create_engine(_test_db_url(), future=True)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
