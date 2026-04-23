import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from emailtriage.db.models import Base
from emailtriage.db.repository import get_results_for_run_era

@pytest.fixture(autouse=True)
async def _use_test_db(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    import emailtriage.db.session as s
    monkeypatch.setattr(s, "AsyncSessionLocal", factory)
    monkeypatch.setattr(s, "engine", engine)

    async def _noop(): pass
    monkeypatch.setattr("emailtriage.agent.runner.init_db", _noop)
    yield
    await engine.dispose()

async def test_agent_runs_end_to_end():
    from emailtriage.agent.runner import run_agent
    from emailtriage.db.session import get_session
    from sqlalchemy import select
    from emailtriage.db.models import DBRun

    run_id = await run_agent()

    async with get_session() as session:
        run_row = (await session.execute(select(DBRun).where(DBRun.id == run_id))).scalar_one()
        results = await get_results_for_run_era(session)

    assert run_row.status == "completed"
    assert run_row.emails_processed == 3
    assert len(results) == 3
    classifications = {r.classification for r in results}
    assert classifications == {"urgent", "follow-up", "ignore"}
    urgent = next(r for r in results if r.classification == "urgent")
    assert urgent.draft_reply is not None
