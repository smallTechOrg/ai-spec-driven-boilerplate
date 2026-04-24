"""SQLAlchemy 2.0 declarative models."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import ForeignKey, Index, String, Text, TIMESTAMP, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SearchRunORM(Base):
    __tablename__ = "search_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    industry: Mapped[str] = mapped_column(String(200), nullable=False)
    size_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class LeadORM(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    search_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("search_runs.id", ondelete="CASCADE"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    domain: Mapped[str] = mapped_column(String(500), nullable=False)
    website: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(200), nullable=True)
    headcount_estimate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    why_fit: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_now
    )

    __table_args__ = (
        Index("ix_leads_domain", "domain", unique=True),
        Index("ix_leads_search_run_id", "search_run_id"),
    )
