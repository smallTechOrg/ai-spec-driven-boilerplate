import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from blogforge.db.models import DBBlog, DBPost, DBRun, DBUsedTopic, DBWriter
from blogforge.domain.models import Blog, Post, Run, UsedTopic, Writer


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Blog ─────────────────────────────────────────────────────────────────────

async def get_blog(session: AsyncSession) -> Blog | None:
    result = await session.execute(select(DBBlog).where(DBBlog.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _blog_to_domain(row)


async def upsert_blog(session: AsyncSession, **fields: object) -> Blog:
    result = await session.execute(select(DBBlog).where(DBBlog.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        now = _now()
        row = DBBlog(id=1, created_at=now, updated_at=now, **fields)  # type: ignore[arg-type]
        session.add(row)
    else:
        for k, v in fields.items():
            if k == "themes":
                row.themes = v  # type: ignore[assignment]
            else:
                setattr(row, k, v)
        row.updated_at = _now()
    await session.flush()
    return _blog_to_domain(row)


def _blog_to_domain(row: DBBlog) -> Blog:
    return Blog(
        id=row.id,
        name=row.name,
        tagline=row.tagline,
        niche=row.niche,
        themes=row.themes,
        posts_per_run=row.posts_per_run,
        schedule_cron=row.schedule_cron,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ── Writers ───────────────────────────────────────────────────────────────────

async def create_writer(session: AsyncSession, name: str, persona_prompt: str, bio: str,
                        avatar_url: str | None = None) -> Writer:
    now = _now()
    row = DBWriter(name=name, persona_prompt=persona_prompt, bio=bio,
                   avatar_url=avatar_url, created_at=now, updated_at=now)
    session.add(row)
    await session.flush()
    return _writer_to_domain(row)


async def get_writers(session: AsyncSession, active_only: bool = False) -> list[Writer]:
    q = select(DBWriter).order_by(DBWriter.id)
    if active_only:
        q = q.where(DBWriter.is_active.is_(True))
    result = await session.execute(q)
    return [_writer_to_domain(r) for r in result.scalars()]


async def get_writer(session: AsyncSession, writer_id: int) -> Writer | None:
    result = await session.execute(select(DBWriter).where(DBWriter.id == writer_id))
    row = result.scalar_one_or_none()
    return _writer_to_domain(row) if row else None


async def update_writer(session: AsyncSession, writer_id: int, **fields: object) -> Writer | None:
    result = await session.execute(select(DBWriter).where(DBWriter.id == writer_id))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        setattr(row, k, v)
    row.updated_at = _now()
    await session.flush()
    return _writer_to_domain(row)


async def deactivate_writer(session: AsyncSession, writer_id: int) -> bool:
    result = await session.execute(select(DBWriter).where(DBWriter.id == writer_id))
    row = result.scalar_one_or_none()
    if row is None:
        return False
    row.is_active = False
    row.updated_at = _now()
    await session.flush()
    return True


def _writer_to_domain(row: DBWriter) -> Writer:
    return Writer(
        id=row.id,
        name=row.name,
        persona_prompt=row.persona_prompt,
        bio=row.bio,
        avatar_url=row.avatar_url,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ── Runs ──────────────────────────────────────────────────────────────────────

async def create_run(session: AsyncSession, trigger: str, posts_requested: int) -> Run:
    row = DBRun(trigger=trigger, status="running",
                posts_requested=posts_requested, started_at=_now())
    session.add(row)
    await session.flush()
    return _run_to_domain(row)


async def update_run(session: AsyncSession, run_id: int, **fields: object) -> Run | None:
    result = await session.execute(select(DBRun).where(DBRun.id == run_id))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        setattr(row, k, v)
    await session.flush()
    return _run_to_domain(row)


async def get_run(session: AsyncSession, run_id: int) -> Run | None:
    result = await session.execute(select(DBRun).where(DBRun.id == run_id))
    row = result.scalar_one_or_none()
    return _run_to_domain(row) if row else None


async def get_runs(session: AsyncSession) -> list[Run]:
    result = await session.execute(select(DBRun).order_by(DBRun.started_at.desc()))
    return [_run_to_domain(r) for r in result.scalars()]


async def get_active_run(session: AsyncSession) -> Run | None:
    result = await session.execute(select(DBRun).where(DBRun.status == "running"))
    row = result.scalar_one_or_none()
    return _run_to_domain(row) if row else None


def _run_to_domain(row: DBRun) -> Run:
    return Run(
        id=row.id,
        trigger=row.trigger,
        status=row.status,
        posts_requested=row.posts_requested,
        posts_completed=row.posts_completed,
        error_message=row.error_message,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


# ── Posts ─────────────────────────────────────────────────────────────────────

async def create_post(session: AsyncSession, run_id: int, writer_id: int, topic: str,
                      title: str, content_markdown: str, content_html: str, slug: str,
                      cover_image_path: str | None = None,
                      cover_image_prompt: str | None = None,
                      status: str = "success") -> Post:
    now = _now()
    row = DBPost(
        run_id=run_id, writer_id=writer_id, topic=topic, title=title,
        content_markdown=content_markdown, content_html=content_html, slug=slug,
        cover_image_path=cover_image_path, cover_image_prompt=cover_image_prompt,
        status=status, published_at=now, created_at=now,
    )
    session.add(row)
    await session.flush()
    return _post_to_domain(row)


async def update_post(session: AsyncSession, post_id: int, **fields: object) -> Post | None:
    result = await session.execute(select(DBPost).where(DBPost.id == post_id))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        setattr(row, k, v)
    await session.flush()
    return _post_to_domain(row)


async def get_posts(session: AsyncSession, writer_id: int | None = None,
                    limit: int = 20, offset: int = 0) -> list[Post]:
    q = select(DBPost).order_by(DBPost.created_at.desc()).limit(limit).offset(offset)
    if writer_id is not None:
        q = q.where(DBPost.writer_id == writer_id)
    result = await session.execute(q)
    return [_post_to_domain(r) for r in result.scalars()]


async def get_posts_for_run(session: AsyncSession, run_id: int) -> list[Post]:
    result = await session.execute(
        select(DBPost).where(DBPost.run_id == run_id).order_by(DBPost.created_at)
    )
    return [_post_to_domain(r) for r in result.scalars()]


def _post_to_domain(row: DBPost) -> Post:
    return Post(
        id=row.id,
        run_id=row.run_id,
        writer_id=row.writer_id,
        topic=row.topic,
        title=row.title,
        content_markdown=row.content_markdown,
        content_html=row.content_html,
        cover_image_path=row.cover_image_path,
        cover_image_prompt=row.cover_image_prompt,
        slug=row.slug,
        status=row.status,
        published_at=row.published_at,
        created_at=row.created_at,
    )


# ── UsedTopics ────────────────────────────────────────────────────────────────

async def add_used_topic(session: AsyncSession, topic: str, post_id: int) -> UsedTopic:
    row = DBUsedTopic(topic=topic.lower().strip(), post_id=post_id, used_at=_now())
    session.add(row)
    await session.flush()
    return UsedTopic(id=row.id, topic=row.topic, post_id=row.post_id, used_at=row.used_at)


async def get_used_topics(session: AsyncSession) -> list[str]:
    result = await session.execute(select(DBUsedTopic.topic))
    return [r for r in result.scalars()]
