"""Full-stack contract test — httpx + ASGI transport, FakeModel, NO key. Exercises the real request/response
path the UI depends on and asserts every field the UI consumes is present (not just a 200)."""
import httpx
import pytest

from agent.server import app
from tests.helpers import TriageFakeModel


@pytest.fixture
def _fake_model(monkeypatch):
    ticket = "I was charged twice for my subscription. Please refund."
    # the server route -> run_agent -> get_model(); patch it so no API key is needed
    monkeypatch.setattr("agent.runner.get_model", lambda: TriageFakeModel(ticket))


async def test_post_runs_returns_ok_envelope_with_answer(_fake_model):
    transport = httpx.ASGITransport(app=app)   # ASGITransport skips the lifespan — server reads checkpointer via getattr
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/runs", json={"goal": "I was charged twice for my subscription. Please refund."})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True                          # the ok() envelope
    data = body["data"]
    # every field the UI consumes must be present
    assert data["status"] == "completed"
    assert data["run_id"]
    assert data["answer"]
    assert "billing" in data["answer"].lower()         # the real classify result flowed through


async def test_health_returns_ok():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
