from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from blogforge.db.models import VoiceRow, WriterRow, ArticleRow, AgentRunRow
from blogforge.domain import Voice, Writer, Article, AgentRun, RunStatus


# --- Voice ---

def create_voice(db: Session, *, name: str, description: str, guidelines: str) -> Voice:
    row = VoiceRow(name=name, description=description, guidelines=guidelines)
    db.add(row)
    db.commit()
    db.refresh(row)
    return Voice.model_validate(row)


def list_voices(db: Session) -> list[Voice]:
    rows = db.execute(select(VoiceRow).order_by(VoiceRow.created_at.desc())).scalars().all()
    return [Voice.model_validate(r) for r in rows]


def get_voice(db: Session, voice_id: UUID) -> Voice | None:
    row = db.get(VoiceRow, voice_id)
    return Voice.model_validate(row) if row else None


# --- Writer ---

def create_writer(db: Session, *, name: str, persona: str, voice_id: UUID) -> Writer:
    row = WriterRow(name=name, persona=persona, voice_id=voice_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return Writer.model_validate(row)


def list_writers(db: Session) -> list[Writer]:
    rows = db.execute(select(WriterRow).order_by(WriterRow.created_at.desc())).scalars().all()
    return [Writer.model_validate(r) for r in rows]


def get_writer(db: Session, writer_id: UUID) -> Writer | None:
    row = db.get(WriterRow, writer_id)
    return Writer.model_validate(row) if row else None


# --- Article ---

def create_article(
    db: Session,
    *,
    writer_id: UUID,
    voice_id: UUID,
    topic: str,
    title: str,
    body: str,
) -> Article:
    row = ArticleRow(writer_id=writer_id, voice_id=voice_id, topic=topic, title=title, body=body)
    db.add(row)
    db.commit()
    db.refresh(row)
    return Article.model_validate(row)


def list_articles(db: Session, limit: int = 50) -> list[Article]:
    rows = (
        db.execute(select(ArticleRow).order_by(ArticleRow.created_at.desc()).limit(limit))
        .scalars()
        .all()
    )
    return [Article.model_validate(r) for r in rows]


def get_article(db: Session, article_id: UUID) -> Article | None:
    row = db.get(ArticleRow, article_id)
    return Article.model_validate(row) if row else None


# --- AgentRun ---

def create_run(db: Session, *, writer_id: UUID, topic: str) -> AgentRun:
    row = AgentRunRow(writer_id=writer_id, topic=topic, status=RunStatus.pending.value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return AgentRun.model_validate(row)


def complete_run(db: Session, run_id: UUID, *, article_id: UUID) -> AgentRun:
    row = db.get(AgentRunRow, run_id)
    assert row is not None
    row.status = RunStatus.completed.value
    row.article_id = article_id
    db.commit()
    db.refresh(row)
    return AgentRun.model_validate(row)


def fail_run(db: Session, run_id: UUID, *, error_message: str) -> AgentRun:
    row = db.get(AgentRunRow, run_id)
    assert row is not None
    row.status = RunStatus.failed.value
    row.error_message = error_message
    db.commit()
    db.refresh(row)
    return AgentRun.model_validate(row)


def get_run(db: Session, run_id: UUID) -> AgentRun | None:
    row = db.get(AgentRunRow, run_id)
    return AgentRun.model_validate(row) if row else None
