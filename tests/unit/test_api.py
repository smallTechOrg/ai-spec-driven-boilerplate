"""API contract tests — no LLM key required, graph is not invoked."""
import pytest


def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_create_session(api_client):
    """POST /sessions creates a session."""
    r = api_client.post("/sessions", json={})
    assert r.status_code == 201
    data = r.json()["data"]
    assert "session_id" in data
    assert "name" in data
    assert data["name"].startswith("Session")


def test_list_sessions_empty(api_client):
    """GET /sessions returns empty list when no sessions exist."""
    r = api_client.get("/sessions")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


def test_get_session_not_found(api_client):
    """GET /sessions/{id} returns 404 for unknown session."""
    r = api_client.get("/sessions/nonexistent-session-id")
    assert r.status_code == 404


def test_create_and_get_session(api_client):
    """Create then fetch a session by ID."""
    create = api_client.post("/sessions", json={})
    assert create.status_code == 201
    session_id = create.json()["data"]["session_id"]

    get = api_client.get(f"/sessions/{session_id}")
    assert get.status_code == 200
    data = get.json()["data"]
    assert data["session_id"] == session_id


def test_runs_returns_501(api_client):
    """Old /runs endpoint returns 501 (replaced by /chat)."""
    r = api_client.post("/runs", json={"input_text": "test"})
    assert r.status_code == 501


def test_list_datasets_requires_session(api_client):
    """GET /datasets?session_id=<nonexistent> returns 404."""
    r = api_client.get("/datasets?session_id=nonexistent")
    assert r.status_code == 404


def test_audit_log_requires_session(api_client):
    """GET /audit?session_id=<nonexistent> returns 404."""
    r = api_client.get("/audit?session_id=nonexistent")
    assert r.status_code == 404


def test_chat_empty_question_rejected(api_client):
    """GET /chat with blank question returns 400 or 422."""
    # First create a session
    create = api_client.post("/sessions", json={})
    session_id = create.json()["data"]["session_id"]
    r = api_client.get(f"/chat?session_id={session_id}&q=")
    assert r.status_code in (400, 422)


def test_chat_missing_session_rejected(api_client):
    """GET /chat with nonexistent session_id returns 404."""
    r = api_client.get("/chat?session_id=nonexistent&q=hello")
    assert r.status_code == 404
