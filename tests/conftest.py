"""Shared pytest fixtures for all tests."""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sourcing_agent.config.settings import reset_settings
from sourcing_agent.db.models import Base
from sourcing_agent.db.session import reset_engine
from sourcing_agent.llm import reset_llm_client


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset all module-level singletons before each test."""
    reset_settings()
    reset_engine()
    reset_llm_client()
    yield
    reset_settings()
    reset_engine()
    reset_llm_client()


def _test_db_url() -> str:
    # Prefer SA_TEST_DATABASE_URL env var; fall back to Settings (reads .env)
    url = os.environ.get("SA_TEST_DATABASE_URL")
    if not url:
        try:
            from sourcing_agent.config.settings import Settings

            s = Settings()
            url = s.test_database_url or s.database_url
        except Exception:
            pass
    if not url:
        raise RuntimeError(
            "SA_TEST_DATABASE_URL (or SA_DATABASE_URL) must be set to run tests. "
            "Example: postgresql://user@localhost:5432/sourcing_test"
        )
    return url


@pytest.fixture(scope="session")
def test_db_url() -> str:
    return _test_db_url()


@pytest.fixture(scope="session")
def db_engine(test_db_url):
    engine = create_engine(test_db_url, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine, monkeypatch):
    """Provide a test DB session and patch the session factory to use it."""
    import sourcing_agent.db.session as db_mod

    test_engine = db_engine
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(db_mod, "_engine", test_engine)
    monkeypatch.setattr(db_mod, "_SessionLocal", TestSessionLocal)

    # Patch settings to point at test DB
    os.environ.setdefault("SA_DATABASE_URL", _test_db_url())
    os.environ.setdefault("SA_GEMINI_API_KEY", "")

    yield TestSessionLocal


@pytest.fixture()
def test_client(db_session, monkeypatch):
    """FastAPI TestClient with test DB wired in."""
    from fastapi.testclient import TestClient

    from sourcing_agent.api import create_app

    os.environ.setdefault("SA_DATABASE_URL", _test_db_url())
    os.environ.setdefault("SA_GEMINI_API_KEY", "")

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
