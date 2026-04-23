import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from prmonitor.db.models import Base

@pytest.fixture(autouse=True)
async def _db(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
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

async def test_pipeline_end_to_end():
    from prmonitor.agent.runner import run_agent
    from prmonitor.db.session import get_session
    from prmonitor.db.repository import get_runs
    run_id = await run_agent()
    async with get_session() as session:
        runs = await get_runs(session)
    assert runs[0].status == "completed"
    assert runs[0].stale_pr_count == 2
    assert run_id == runs[0].id
