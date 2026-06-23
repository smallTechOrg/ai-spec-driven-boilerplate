"""Integration tests for the analyst agent pipeline — require real AGENT_GEMINI_API_KEY."""
import pytest
import io
import json
from sqlalchemy.orm import Session

from db import session as session_module
from db.models import SessionRow, DatasetRow, MessageRow


@pytest.mark.usefixtures("_require_llm_key")
def test_create_session_and_list(_isolated_db, api_client):
    """Create a session; it should appear in the list."""
    r = api_client.post("/sessions", json={})
    assert r.status_code == 201
    session_id = r.json()["data"]["session_id"]

    list_r = api_client.get("/sessions")
    assert list_r.status_code == 200
    ids = [s["session_id"] for s in list_r.json()["data"]]
    assert session_id in ids


@pytest.mark.usefixtures("_require_llm_key")
def test_upload_csv_dataset(_isolated_db, api_client):
    """Upload a CSV and verify schema is inferred."""
    # Create session
    session_id = api_client.post("/sessions", json={}).json()["data"]["session_id"]

    # Upload a small CSV
    csv_content = b"name,age,score\nAlice,30,95.5\nBob,25,87.3\nCharlie,35,91.0\n"
    files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
    data = {"session_id": session_id}
    r = api_client.post("/datasets", files=files, data=data)
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["name"] == "test.csv"
    assert d["row_count"] == 3
    assert len(d["columns"]) == 3
    col_names = [c["name"] for c in d["columns"]]
    assert "name" in col_names
    assert "age" in col_names
    assert "score" in col_names


@pytest.mark.usefixtures("_require_llm_key")
def test_audit_log_empty(_isolated_db, api_client):
    """Audit log is empty for a new session."""
    session_id = api_client.post("/sessions", json={}).json()["data"]["session_id"]
    r = api_client.get(f"/audit?session_id={session_id}")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["total"] == 0
    assert body["entries"] == []


@pytest.mark.usefixtures("_require_llm_key")
def test_session_persists_datasets(_isolated_db, api_client):
    """After uploading a dataset, GET /sessions/{id} shows it."""
    session_id = api_client.post("/sessions", json={}).json()["data"]["session_id"]

    csv_content = b"product,sales\nWidget A,1000\nWidget B,2000\n"
    files = {"file": ("sales.csv", io.BytesIO(csv_content), "text/csv")}
    api_client.post("/datasets", files=files, data={"session_id": session_id})

    r = api_client.get(f"/sessions/{session_id}")
    assert r.status_code == 200
    datasets = r.json()["data"]["datasets"]
    assert len(datasets) == 1
    assert datasets[0]["name"] == "sales.csv"
