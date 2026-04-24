"""
Shared test fixtures.

Before running tests, set DATABASE_URL (or LGA_DATABASE_URL) to point at a real
PostgreSQL test database (e.g. lead_gen_agent_test).

The fixture creates all tables before the test session and drops them after.
"""
import os

import pytest
from sqlalchemy import create_engine, text

from lead_gen_agent.db.models import Base
from lead_gen_agent.db.session import reset_engine


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    """Create schema on the test DB; tear it down after all tests."""
    # Allow either the app prefix or bare DATABASE_URL for convenience in CI
    db_url = (
        os.environ.get("LGA_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
    )
    if not db_url:
        pytest.skip("LGA_DATABASE_URL not set — skipping DB tests")

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Reset the settings singleton between tests so env patches take effect."""
    import lead_gen_agent.config as cfg
    cfg._settings = None
    reset_engine()
    yield
    cfg._settings = None
    reset_engine()
