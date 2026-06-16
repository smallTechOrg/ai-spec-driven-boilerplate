"""Golden-path UI smoke test: upload CSV, ask question, see answer."""
import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import data_analysis_agent.db.session as session_module
from data_analysis_agent.db.models import Base


@pytest.fixture(autouse=True)
def _stub_env(monkeypatch):
    monkeypatch.setenv("DATAANALYSIS_DATABASE_URL", "sqlite:///golden_test.db")
    monkeypatch.delenv("DATAANALYSIS_OPENROUTER_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _use_sqlite(tmp_path, monkeypatch):
    db_path = tmp_path / "golden.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(session_module, "_engine", engine)
    monkeypatch.setattr(session_module, "_SessionLocal", factory)
    monkeypatch.setattr(session_module, "init_db", lambda: None)

    yield

    engine.dispose()
    monkeypatch.setattr(session_module, "_engine", None)
    monkeypatch.setattr(session_module, "_SessionLocal", None)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATAANALYSIS_UPLOAD_DIR", str(tmp_path / "uploads"))
    import data_analysis_agent.llm.client as llm_module
    llm_module._client = None

    from data_analysis_agent.api import create_app
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def _make_csv() -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["product", "revenue", "units"])
    writer.writerow(["Widget A", 5000, 25])
    writer.writerow(["Widget B", 3000, 15])
    return buf.getvalue().encode()


def test_home_page_loads(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Upload" in r.text


def test_stub_banner_visible_on_home(client):
    r = client.get("/")
    assert "Stub mode" in r.text


def test_upload_csv_and_ask_question(client, tmp_path):
    # 1. Upload CSV
    csv_bytes = _make_csv()
    r = client.post(
        "/upload",
        files={"file": ("test_data.csv", csv_bytes, "text/csv")},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert "test_data.csv" in r.text or "product" in r.text.lower()

    # Extract dataset_id from the redirect URL
    dataset_url = r.url
    dataset_id = str(dataset_url).rstrip("/").split("/")[-1]

    # 2. Ask a question
    r2 = client.post(
        f"/datasets/{dataset_id}/query",
        data={"question": "What is the total revenue?"},
        follow_redirects=True,
    )
    assert r2.status_code == 200
    assert "total revenue" in r2.text.lower() or "answer" in r2.text.lower()
    # Answer should be present (stub produces non-empty text)
    assert "stub" in r2.text.lower() or "analysis" in r2.text.lower()


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
