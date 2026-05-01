from __future__ import annotations

import os

import pytest

# Default to the local test DB if the caller didn't set one.
os.environ.setdefault(
    "LEADGEN_DATABASE_URL",
    "postgresql+psycopg2://sai@localhost:5432/lead_gen_agent_test",
)
os.environ["LEADGEN_LLM_PROVIDER"] = "stub"


@pytest.fixture(autouse=True)
def _reset_settings_singleton():
    import lead_gen_agent.config.settings as m
    m._settings = None
    yield
    m._settings = None


@pytest.fixture(autouse=True)
def _reset_db_singletons():
    import lead_gen_agent.db.session as s
    s._engine = None
    s._SessionLocal = None
    yield
    s._engine = None
    s._SessionLocal = None


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create all tables in the test DB before the session; truncate between tests."""
    from sqlalchemy import create_engine
    from lead_gen_agent.db.models import Base
    url = os.environ["LEADGEN_DATABASE_URL"]
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate all tables before each test for isolation."""
    from sqlalchemy import create_engine, text
    url = os.environ["LEADGEN_DATABASE_URL"]
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE leads, runs RESTART IDENTITY CASCADE"))
    engine.dispose()
    yield
