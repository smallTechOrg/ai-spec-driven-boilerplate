"""POST /api/run drives the slice and persists a Run row — offline, stub LLM."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api.app import app
from src.db.models import Run


async def test_run_returns_contract_and_persists_row(db_session):
    # db_session points AsyncSessionLocal at a throwaway DB and stubs init_db,
    # so the TestClient lifespan does not rebuild the engine.
    with TestClient(app) as client:
        resp = client.post("/api/run", json={"input": "hello world"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["result"].startswith("[STUB] Done.")
    assert isinstance(body["data"]["run_id"], int)

    # The persistence loop is live: one Run row, input preserved.
    rows = (await db_session.execute(select(Run))).scalars().all()
    assert len(rows) == 1
    assert rows[0].input == "hello world"
    assert rows[0].id == body["data"]["run_id"]


async def test_run_rejects_empty_input(db_session):
    with TestClient(app) as client:
        resp = client.post("/api/run", json={"input": "   "})
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
