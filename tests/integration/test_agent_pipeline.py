"""Phase 2 gate: agent runs end-to-end with stubs; post in DB; run completed; zero real API calls."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from blogforge.db.models import Base
from blogforge.db.repository import (
    create_writer,
    get_posts_for_run,
    get_run,
    upsert_blog,
)
from blogforge.db.session import AsyncSessionLocal


@pytest.fixture(autouse=True)
async def _use_test_db(monkeypatch, tmp_path):
    """Point the session factory at an in-memory SQLite DB for this test."""
    db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    import blogforge.db.session as session_mod
    monkeypatch.setattr(session_mod, "AsyncSessionLocal", factory)

    yield

    await engine.dispose()


async def test_agent_runs_end_to_end_with_stubs():
    from blogforge.agent.runner import run_agent
    from blogforge.db.session import get_session

    # Seed blog + writer
    async with get_session() as session:
        await upsert_blog(session, name="TestBlog", niche="productivity", themes=["focus"])
        await create_writer(session, name="Alice", persona_prompt="Write clearly.", bio="")

    run_id = await run_agent(trigger="test", posts_count=3)

    async with get_session() as session:
        run = await get_run(session, run_id)
        posts = await get_posts_for_run(session, run_id)

    assert run is not None
    assert run.status == "completed", f"Expected 'completed', got '{run.status}'"
    assert len(posts) == 3, f"Expected 3 posts, got {len(posts)}"
    for post in posts:
        assert post.title
        assert post.content_markdown
        assert post.cover_image_path is not None
