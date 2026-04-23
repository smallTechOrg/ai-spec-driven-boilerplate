import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from blogforge.db import repository as repo
from blogforge.domain.models import Blog, Post, Run, Writer


# ── Blog ──────────────────────────────────────────────────────────────────────

async def test_get_blog_returns_none_when_not_created(db_session: AsyncSession) -> None:
    result = await repo.get_blog(db_session)
    assert result is None


async def test_upsert_blog_creates_blog(db_session: AsyncSession) -> None:
    blog = await repo.upsert_blog(db_session, name="Test Blog", niche="AI tools",
                                   themes=["automation", "productivity"])
    assert isinstance(blog, Blog)
    assert blog.name == "Test Blog"
    assert blog.niche == "AI tools"
    assert blog.themes == ["automation", "productivity"]
    assert blog.id == 1


async def test_upsert_blog_updates_existing(db_session: AsyncSession) -> None:
    await repo.upsert_blog(db_session, name="Original", niche="Tech")
    updated = await repo.upsert_blog(db_session, name="Updated", niche="Tech")
    assert updated.name == "Updated"


async def test_get_blog_returns_created_blog(db_session: AsyncSession) -> None:
    await repo.upsert_blog(db_session, name="My Blog", niche="Startups")
    blog = await repo.get_blog(db_session)
    assert blog is not None
    assert blog.name == "My Blog"


# ── Writers ───────────────────────────────────────────────────────────────────

async def test_create_writer_returns_domain_model(db_session: AsyncSession) -> None:
    writer = await repo.create_writer(db_session, name="Alex", persona_prompt="Be concise.",
                                      bio="Alex writes about AI.")
    assert isinstance(writer, Writer)
    assert writer.name == "Alex"
    assert writer.is_active is True
    assert writer.id > 0


async def test_get_writers_returns_all(db_session: AsyncSession) -> None:
    await repo.create_writer(db_session, name="Alex", persona_prompt="P1", bio="B1")
    await repo.create_writer(db_session, name="Sam", persona_prompt="P2", bio="B2")
    writers = await repo.get_writers(db_session)
    assert len(writers) == 2


async def test_get_writers_active_only(db_session: AsyncSession) -> None:
    w = await repo.create_writer(db_session, name="Alex", persona_prompt="P1", bio="B1")
    await repo.create_writer(db_session, name="Sam", persona_prompt="P2", bio="B2")
    await repo.deactivate_writer(db_session, w.id)
    active = await repo.get_writers(db_session, active_only=True)
    assert len(active) == 1
    assert active[0].name == "Sam"


async def test_update_writer_changes_fields(db_session: AsyncSession) -> None:
    writer = await repo.create_writer(db_session, name="Alex", persona_prompt="P1", bio="B1")
    updated = await repo.update_writer(db_session, writer.id, bio="Updated bio")
    assert updated is not None
    assert updated.bio == "Updated bio"


async def test_deactivate_writer_sets_inactive(db_session: AsyncSession) -> None:
    writer = await repo.create_writer(db_session, name="Alex", persona_prompt="P1", bio="B1")
    success = await repo.deactivate_writer(db_session, writer.id)
    assert success is True
    fetched = await repo.get_writer(db_session, writer.id)
    assert fetched is not None
    assert fetched.is_active is False


async def test_deactivate_nonexistent_writer_returns_false(db_session: AsyncSession) -> None:
    result = await repo.deactivate_writer(db_session, 9999)
    assert result is False


# ── Runs ──────────────────────────────────────────────────────────────────────

async def test_create_run_returns_running_status(db_session: AsyncSession) -> None:
    run = await repo.create_run(db_session, trigger="manual", posts_requested=3)
    assert isinstance(run, Run)
    assert run.status == "running"
    assert run.trigger == "manual"
    assert run.posts_requested == 3
    assert run.posts_completed == 0


async def test_update_run_to_completed(db_session: AsyncSession) -> None:
    run = await repo.create_run(db_session, trigger="manual", posts_requested=3)
    from datetime import datetime, timezone
    updated = await repo.update_run(db_session, run.id, status="completed",
                                    posts_completed=3,
                                    completed_at=datetime.now(timezone.utc))
    assert updated is not None
    assert updated.status == "completed"
    assert updated.posts_completed == 3


async def test_get_runs_newest_first(db_session: AsyncSession) -> None:
    await repo.create_run(db_session, trigger="manual", posts_requested=1)
    await repo.create_run(db_session, trigger="scheduled", posts_requested=2)
    runs = await repo.get_runs(db_session)
    assert len(runs) == 2
    assert runs[0].trigger == "scheduled"


async def test_get_active_run_finds_running(db_session: AsyncSession) -> None:
    run = await repo.create_run(db_session, trigger="manual", posts_requested=1)
    active = await repo.get_active_run(db_session)
    assert active is not None
    assert active.id == run.id


async def test_get_active_run_none_when_all_complete(db_session: AsyncSession) -> None:
    run = await repo.create_run(db_session, trigger="manual", posts_requested=1)
    await repo.update_run(db_session, run.id, status="completed")
    active = await repo.get_active_run(db_session)
    assert active is None


# ── Posts ─────────────────────────────────────────────────────────────────────

async def _setup_run_and_writer(session: AsyncSession) -> tuple[int, int]:
    run = await repo.create_run(session, trigger="manual", posts_requested=1)
    writer = await repo.create_writer(session, name="Alex", persona_prompt="P", bio="B")
    return run.id, writer.id


async def test_create_post_returns_domain_model(db_session: AsyncSession) -> None:
    run_id, writer_id = await _setup_run_and_writer(db_session)
    post = await repo.create_post(
        db_session, run_id=run_id, writer_id=writer_id,
        topic="AI in 2026", title="The Future of AI",
        content_markdown="## Intro\nHello world",
        content_html="<h2>Intro</h2><p>Hello world</p>",
        slug="the-future-of-ai-2026-04",
    )
    assert isinstance(post, Post)
    assert post.title == "The Future of AI"
    assert post.slug == "the-future-of-ai-2026-04"
    assert post.status == "success"


async def test_get_posts_returns_newest_first(db_session: AsyncSession) -> None:
    run_id, writer_id = await _setup_run_and_writer(db_session)
    await repo.create_post(db_session, run_id=run_id, writer_id=writer_id,
                            topic="T1", title="Post 1", content_markdown="x",
                            content_html="<p>x</p>", slug="post-1")
    await repo.create_post(db_session, run_id=run_id, writer_id=writer_id,
                            topic="T2", title="Post 2", content_markdown="y",
                            content_html="<p>y</p>", slug="post-2")
    posts = await repo.get_posts(db_session)
    assert len(posts) == 2
    assert posts[0].slug == "post-2"


async def test_get_posts_filter_by_writer(db_session: AsyncSession) -> None:
    run_id, writer_id = await _setup_run_and_writer(db_session)
    other_writer = await repo.create_writer(db_session, name="Sam", persona_prompt="P2", bio="B2")
    await repo.create_post(db_session, run_id=run_id, writer_id=writer_id,
                            topic="T1", title="P1", content_markdown="x",
                            content_html="<p>x</p>", slug="p-1")
    await repo.create_post(db_session, run_id=run_id, writer_id=other_writer.id,
                            topic="T2", title="P2", content_markdown="y",
                            content_html="<p>y</p>", slug="p-2")
    posts = await repo.get_posts(db_session, writer_id=writer_id)
    assert len(posts) == 1
    assert posts[0].slug == "p-1"


# ── UsedTopics ────────────────────────────────────────────────────────────────

async def test_add_used_topic_normalises_case(db_session: AsyncSession) -> None:
    run_id, writer_id = await _setup_run_and_writer(db_session)
    post = await repo.create_post(db_session, run_id=run_id, writer_id=writer_id,
                                   topic="AI Trends", title="T", content_markdown="x",
                                   content_html="<p>x</p>", slug="ai-trends-2026")
    used = await repo.add_used_topic(db_session, topic="AI Trends", post_id=post.id)
    assert used.topic == "ai trends"


async def test_get_used_topics_returns_normalised_list(db_session: AsyncSession) -> None:
    run_id, writer_id = await _setup_run_and_writer(db_session)
    post = await repo.create_post(db_session, run_id=run_id, writer_id=writer_id,
                                   topic="Topic One", title="T", content_markdown="x",
                                   content_html="<p>x</p>", slug="topic-one-2026")
    await repo.add_used_topic(db_session, topic="Topic One", post_id=post.id)
    topics = await repo.get_used_topics(db_session)
    assert "topic one" in topics


async def test_get_used_topics_empty_initially(db_session: AsyncSession) -> None:
    topics = await repo.get_used_topics(db_session)
    assert topics == []
