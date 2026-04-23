import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from prmonitor.db.models import Base
from prmonitor.db.repository import get_runs

@pytest.fixture(autouse=True)
async def _use_test_db(monkeypatch, tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    import prmonitor.db.session as s
    monkeypatch.setattr(s, "AsyncSessionLocal", factory)
    monkeypatch.setattr(s, "engine", engine)

    async def _noop(): pass
    monkeypatch.setattr("prmonitor.agent.runner.init_db", _noop)
    yield
    await engine.dispose()

async def test_agent_runs_end_to_end():
    from prmonitor.agent.runner import run_agent
    from prmonitor.db.session import get_session

    run_id = await run_agent()

    async with get_session() as session:
        runs = await get_runs(session)

    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].stale_pr_count == 3
    assert run_id == runs[0].id
