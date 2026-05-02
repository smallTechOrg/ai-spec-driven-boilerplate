import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from up_police_ai.db.models import Base
import up_police_ai.db.session as session_module
import up_police_ai.config.settings as settings_module

TEST_DB_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/up_police_ai_test")


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    session_module._engine = engine
    session_module._SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def _reset_settings():
    settings_module._settings = None
    yield
    settings_module._settings = None
