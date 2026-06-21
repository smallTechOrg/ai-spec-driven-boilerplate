from fastapi.testclient import TestClient

from src.api.app import app


def test_health_ok_and_stub_mode():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["stub_mode"] is True
    assert body["llm_provider"] == "stub"
