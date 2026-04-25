from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, TIMESTAMP, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SourcingRequestRow(Base):
    __tablename__ = "sourcing_requests"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    material: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeline: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_now
    )

    runs: Mapped[list[RunRow]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(
        Text, ForeignKey("sourcing_requests.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    llm_provider: Mapped[str] = mapped_column(Text, nullable=False, default="stub")
    search_provider: Mapped[str] = mapped_column(Text, nullable=False, default="stub")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    request: Mapped[SourcingRequestRow] = relationship(back_populates="runs")
    suppliers: Mapped[list[SupplierRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list[RecommendationRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class SupplierRow(Base):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        Text, ForeignKey("runs.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_indication: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_time: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[RunRow] = relationship(back_populates="suppliers")


class RecommendationRow(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        Text, ForeignKey("runs.id"), nullable=False
    )
    supplier_id: Mapped[str] = mapped_column(
        Text, ForeignKey("suppliers.id"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    run: Mapped[RunRow] = relationship(back_populates="recommendations")
