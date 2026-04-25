"""Golden-path UI smoke test — walks the full primary user flow via TestClient.

Verifies response content, not only status codes.
"""

import os
import time
import uuid


def test_golden_path_home_page(test_client):
    """Home page renders the project form."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert "Sourcing" in response.text
    assert "project_name" in response.text
    assert "material_name" in response.text


def test_golden_path_create_run_and_report(test_client, db_session, monkeypatch):
    """Full flow: submit form → status page → report page with recommendations."""
    monkeypatch.setenv("SA_GEMINI_API_KEY", "")
    monkeypatch.setenv("SA_LLM_PROVIDER", "auto")

    # Submit form
    response = test_client.post(
        "/runs",
        data={
            "project_name": "Smoke Test Project",
            "material_name[]": ["Portland Cement", "Clay Bricks"],
            "quantity[]": ["100", "2000"],
            "unit[]": ["bags", "units"],
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    run_id = location.rstrip("/").split("/")[-1]

    # Status page renders
    status_resp = test_client.get(f"/runs/{run_id}")
    assert status_resp.status_code == 200
    assert "Smoke Test Project" in status_resp.text

    # Poll until completed (stub should finish fast)
    from sourcing_agent.graph.runner import run_agent

    run_agent(uuid.UUID(run_id))

    # Report page renders with supplier data
    report_resp = test_client.get(f"/runs/{run_id}/report")
    assert report_resp.status_code == 200
    assert "Portland Cement" in report_resp.text
    assert "Clay Bricks" in report_resp.text
    # Should have recommendation rows
    assert "Rank" in report_resp.text
    assert "Supplier" in report_resp.text


def test_golden_path_api_create_run(test_client, monkeypatch):
    """API endpoint creates a run and returns run_id."""
    monkeypatch.setenv("SA_GEMINI_API_KEY", "")

    response = test_client.post(
        "/api/runs",
        json={
            "project_name": "API Test",
            "materials": [
                {"name": "Sand", "quantity": 10, "unit": "tonnes"},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "pending"


def test_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_stub_banner_visible(test_client, monkeypatch):
    """Stub mode banner must appear on every page when no API key is set."""
    monkeypatch.setenv("SA_GEMINI_API_KEY", "")
    monkeypatch.setenv("SA_LLM_PROVIDER", "auto")

    response = test_client.get("/")
    assert response.status_code == 200
    assert "stub mode" in response.text.lower()


def test_form_validation_missing_project_name(test_client):
    response = test_client.post(
        "/runs",
        data={
            "project_name": "",
            "material_name[]": ["Cement"],
            "quantity[]": ["100"],
            "unit[]": ["bags"],
        },
        follow_redirects=False,
    )
    # Should return 200 with error, not redirect
    assert response.status_code == 200
    assert "required" in response.text.lower() or "error" in response.text.lower()
