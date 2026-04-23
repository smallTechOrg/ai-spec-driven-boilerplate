import os
import pytest

# Point the app at the test DB before any blogforge imports
os.environ.setdefault(
    "BLOGFORGE_DATABASE_URL",
    os.environ.get(
        "BLOGFORGE_TEST_DATABASE_URL",
        "postgresql+psycopg2://sai@localhost:5432/blogforge_test",
    ),
)
os.environ.setdefault("BLOGFORGE_LLM_PROVIDER", "stub")

from blogforge.config.settings import reset_settings, get_settings  # noqa: E402
from blogforge.db.models import Base  # noqa: E402
from blogforge.db.session import get_engine, new_session, reset_session_cache  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    reset_settings()
    reset_session_cache()
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db():
    session = new_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _clean_tables():
    # Clean between tests so IDs and rowcounts are predictable.
    engine = get_engine()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.exec_driver_sql(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE;')
    yield
