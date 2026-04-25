"""SQLAlchemy 2.0 declarative models for the sourcing agent."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SourcingRun(Base):
    __tablename__ = "sourcing_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    line_items: Mapped[list["MaterialLineItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["SupplierRecommendation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class MaterialLineItem(Base):
    __tablename__ = "material_line_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_runs.id"), nullable=False
    )
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    run: Mapped["SourcingRun"] = relationship(back_populates="line_items")
    recommendations: Mapped[list["SupplierRecommendation"]] = relationship(
        back_populates="line_item", cascade="all, delete-orphan"
    )


class SupplierRecommendation(Base):
    __tablename__ = "supplier_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_runs.id"), nullable=False
    )
    line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_line_items.id"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    supplier_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    certifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["SourcingRun"] = relationship(back_populates="recommendations")
    line_item: Mapped["MaterialLineItem"] = relationship(back_populates="recommendations")
