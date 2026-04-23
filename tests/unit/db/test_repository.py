from prmonitor.db.repository import create_run, update_run, get_runs

async def test_create_and_update(db_session):
    run = await create_run(db_session)
    assert run.status == "running"
    await update_run(db_session, run.id, status="completed", stale_pr_count=5)
    runs = await get_runs(db_session)
    assert runs[0].status == "completed"
    assert runs[0].stale_pr_count == 5

async def test_get_runs_empty(db_session):
    assert await get_runs(db_session) == []
