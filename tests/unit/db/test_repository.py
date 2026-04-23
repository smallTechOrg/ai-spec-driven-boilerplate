import pytest
from prmonitor.db.repository import create_run, update_run, get_runs

async def test_create_run(db_session):
    run = await create_run(db_session)
    assert run.id is not None
    assert run.status == "running"

async def test_update_run(db_session):
    run = await create_run(db_session)
    updated = await update_run(db_session, run.id, status="completed", stale_pr_count=3)
    assert updated.status == "completed"
    assert updated.stale_pr_count == 3

async def test_get_runs(db_session):
    await create_run(db_session)
    await create_run(db_session)
    runs = await get_runs(db_session)
    assert len(runs) == 2
