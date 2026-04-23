import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from food_tracker.config.settings import Settings, get_settings
from food_tracker.db.models import Base


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://localhost/food_tracker_test"
)


@pytest.fixture(scope="session", autouse=True)
def override_settings():
    """Override settings singleton to point at the test database."""
    get_settings.cache_clear()
    os.environ.setdefault("FOOD_TRACKER_DATABASE_URL", TEST_DATABASE_URL)
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def db_engine(override_settings):
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Each test gets a session that rolls back after the test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
