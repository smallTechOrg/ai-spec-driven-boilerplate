import pytest
import json
from pathlib import Path


@pytest.fixture(autouse=True)
def _reset_settings_singleton():
    import config.settings as m
    m._settings = None
    yield
    m._settings = None


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db.models import Base
    import db.session as session_module

    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(session_module, "_engine", engine)
    monkeypatch.setattr(session_module, "_SessionLocal", factory)
    monkeypatch.setattr(session_module, "init_db", lambda: None)
    monkeypatch.setenv("AGENT_DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("AGENT_TEMP_DIR", str(tmp_path / "uploads"))
    yield engine
    engine.dispose()


@pytest.fixture
def _require_llm_key():
    from config.settings import get_settings
    s = get_settings()
    if not s.gemini_api_key and not s.anthropic_api_key:
        pytest.skip("No LLM key set in .env")


@pytest.fixture
def api_client(_isolated_db):
    from fastapi.testclient import TestClient
    from api import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_csv(tmp_path):
    """A small realistic CSV for testing."""
    csv_content = """region,revenue,units,date
West,12500.0,120,2024-01-15
East,8750.5,85,2024-01-15
North,6200.0,62,2024-02-10
South,9800.0,98,2024-02-10
West,14200.0,140,2024-03-05
East,7500.0,75,2024-03-05
North,5800.0,58,2024-04-01
South,11000.0,110,2024-04-01
West,13100.0,130,2024-05-15
East,9200.0,92,2024-05-15
"""
    p = tmp_path / "sales.csv"
    p.write_text(csv_content)
    return p
