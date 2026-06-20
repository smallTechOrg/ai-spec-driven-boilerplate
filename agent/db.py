import datetime as dt
import uuid
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from .config import get_settings


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"
    id:            Mapped[str]           = mapped_column(String, primary_key=True, default=_uuid)
    goal:          Mapped[str]           = mapped_column(Text)
    status:        Mapped[str]           = mapped_column(String, default="running")
    answer:        Mapped[str | None]    = mapped_column(Text, nullable=True)
    iterations:    Mapped[int]           = mapped_column(Integer, default=0)
    input_tokens:  Mapped[int]           = mapped_column(Integer, default=0)
    output_tokens: Mapped[int]           = mapped_column(Integer, default=0)
    cost_usd:      Mapped[float]         = mapped_column(Float, default=0.0)
    thread_id:     Mapped[str | None]    = mapped_column(String, nullable=True, index=True)
    created_at:    Mapped[dt.datetime]   = mapped_column(DateTime(timezone=True), default=_now)


class Message(Base):
    __tablename__ = "messages"
    id:         Mapped[str]           = mapped_column(String, primary_key=True, default=_uuid)
    run_id:     Mapped[str]           = mapped_column(ForeignKey("runs.id"), index=True)
    role:       Mapped[str]           = mapped_column(String)
    content:    Mapped[str]           = mapped_column(Text)
    created_at: Mapped[dt.datetime]   = mapped_column(DateTime(timezone=True), default=_now)


class Span(Base):
    __tablename__ = "spans"
    id:          Mapped[str]           = mapped_column(String, primary_key=True, default=_uuid)
    run_id:      Mapped[str]           = mapped_column(ForeignKey("runs.id"), index=True)
    name:        Mapped[str]           = mapped_column(String)
    kind:        Mapped[str]           = mapped_column(String, default="INTERNAL")
    attributes:  Mapped[dict]          = mapped_column(JSON, default=dict)
    start_ms:    Mapped[float]         = mapped_column(Float)
    end_ms:      Mapped[float]         = mapped_column(Float)
    duration_ms: Mapped[float]         = mapped_column(Float)
    created_at:  Mapped[dt.datetime]   = mapped_column(DateTime(timezone=True), default=_now)


class Memory(Base):
    __tablename__ = "memories"
    id:         Mapped[str]           = mapped_column(String, primary_key=True, default=_uuid)
    content:    Mapped[str]           = mapped_column(Text)
    created_at: Mapped[dt.datetime]   = mapped_column(DateTime(timezone=True), default=_now)


engine = create_async_engine(get_settings().database_url)
_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


def get_sessionmaker() -> async_sessionmaker:
    return _sessionmaker


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
