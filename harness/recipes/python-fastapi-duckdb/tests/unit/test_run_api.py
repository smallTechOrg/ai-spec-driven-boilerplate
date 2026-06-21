"""POST /api/run drives the vertical slice and persists a Run row."""

from sqlalchemy import select

import src.db.session as db_session_module
from src.api.app import app
from src.db.models import Run


async def test_run_api_persists_run(db_session):
    from fastapi.testclient import TestClient

    # TestClient triggers lifespan (init_db); db_session has already patched it to a
    # no-op and swapped AsyncSessionLocal to the throwaway engine.
    with TestClient(app) as client:
        resp = client.post("/api/run", json={"input": "ping"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["result"].startswith("[STUB] Done.")
    assert isinstance(body["data"]["run_id"], int)

    # A Run row landed through the DB layer. Read in a fresh session so we see the
    # route's committed write (not a stale snapshot from the fixture session).
    async with db_session_module.AsyncSessionLocal() as session:
        rows = (await session.execute(select(Run))).scalars().all()
    assert len(rows) == 1
    assert rows[0].input == "ping"
    assert rows[0].result.startswith("[STUB] Done.")
