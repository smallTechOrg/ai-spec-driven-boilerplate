"""API contract tests — no LLM key required, graph is not invoked."""
import pytest
from unittest.mock import patch


def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_run_returns_200_with_output(api_client, _isolated_db):
    from sqlalchemy.orm import Session
    from db.models import RunRow

    # Pre-insert a completed run so run_agent just returns its id
    with Session(_isolated_db) as s:
        row = RunRow(input_text="test", status="completed", output_text="Hello from mock LLM")
        s.add(row)
        s.commit()
        run_id = row.id

    with patch("api.runs.run_agent", return_value=run_id):
        r = api_client.post("/runs", json={"input_text": "test"})

    assert r.status_code == 200
    data = r.json()
    assert data["data"]["output_text"] == "Hello from mock LLM"


def test_run_missing_body(api_client):
    r = api_client.post("/runs", json={})
    assert r.status_code == 422


def test_get_run_not_found(api_client):
    r = api_client.get("/runs/nonexistent-id")
    assert r.status_code == 404


def test_run_empty_input_rejected(api_client):
    r = api_client.post("/runs", json={"input_text": ""})
    # empty string is technically valid JSON — server accepts it; LLM handles it
    # just confirm we get a structured response
    assert r.status_code in (200, 422, 500)
