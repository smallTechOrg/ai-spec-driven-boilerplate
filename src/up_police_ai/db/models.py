import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Float, ForeignKey, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OfficerRow(Base):
    __tablename__ = "officers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    badge_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )

    assessment: Mapped[Optional["AssessmentRow"]] = relationship(
        "AssessmentRow", back_populates="officer", uselist=False
    )
    learning_plan: Mapped[Optional["LearningPlanRow"]] = relationship(
        "LearningPlanRow", back_populates="officer", uselist=False
    )


class AssessmentRow(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    officer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("officers.id"), nullable=False
    )

    # Section A scores
    score_a1: Mapped[float] = mapped_column(Float, nullable=False)
    score_a2: Mapped[float] = mapped_column(Float, nullable=False)
    score_a3: Mapped[float] = mapped_column(Float, nullable=False)
    score_a4: Mapped[float] = mapped_column(Float, nullable=False)
    score_a5: Mapped[float] = mapped_column(Float, nullable=False)

    # Section B scores
    score_b1: Mapped[float] = mapped_column(Float, nullable=False)
    score_b2: Mapped[float] = mapped_column(Float, nullable=False)
    score_b3: Mapped[float] = mapped_column(Float, nullable=False)
    score_b4: Mapped[float] = mapped_column(Float, nullable=False)
    score_b5: Mapped[float] = mapped_column(Float, nullable=False)

    # Section C scores
    score_c1: Mapped[float] = mapped_column(Float, nullable=False)
    score_c2: Mapped[float] = mapped_column(Float, nullable=False)
    score_c3: Mapped[float] = mapped_column(Float, nullable=False)
    score_c4: Mapped[float] = mapped_column(Float, nullable=False)
    score_c5: Mapped[float] = mapped_column(Float, nullable=False)

    # Section D scores
    score_d1: Mapped[float] = mapped_column(Float, nullable=False)
    score_d2: Mapped[float] = mapped_column(Float, nullable=False)
    score_d3: Mapped[float] = mapped_column(Float, nullable=False)
    score_d4: Mapped[float] = mapped_column(Float, nullable=False)
    score_d5: Mapped[float] = mapped_column(Float, nullable=False)

    # Section averages
    avg_a: Mapped[float] = mapped_column(Float, nullable=False)
    avg_b: Mapped[float] = mapped_column(Float, nullable=False)
    avg_c: Mapped[float] = mapped_column(Float, nullable=False)
    avg_d: Mapped[float] = mapped_column(Float, nullable=False)
    avg_overall: Mapped[float] = mapped_column(Float, nullable=False)

    completed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )

    officer: Mapped["OfficerRow"] = relationship("OfficerRow", back_populates="assessment")
    learning_plan: Mapped[Optional["LearningPlanRow"]] = relationship(
        "LearningPlanRow", back_populates="assessment", uselist=False
    )


class LearningPlanRow(Base):
    __tablename__ = "learning_plans"
    __table_args__ = (UniqueConstraint("officer_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    officer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("officers.id"), nullable=False, unique=True
    )
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessments.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )

    officer: Mapped["OfficerRow"] = relationship("OfficerRow", back_populates="learning_plan")
    assessment: Mapped["AssessmentRow"] = relationship("AssessmentRow", back_populates="learning_plan")
    days: Mapped[list["PlanDayRow"]] = relationship(
        "PlanDayRow", back_populates="plan", order_by="PlanDayRow.day_number"
    )


class PlanDayRow(Base):
    __tablename__ = "plan_days"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("learning_plans.id"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(nullable=False)
    focus_area: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    task_key: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    plan: Mapped["LearningPlanRow"] = relationship("LearningPlanRow", back_populates="days")
