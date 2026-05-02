"""Tests that ORM models can be created and queried against the test DB."""

import uuid
from datetime import datetime, timezone

import pytest

from up_police_ai.db.models import (
    AssessmentRow,
    LearningPlanRow,
    OfficerRow,
    PlanDayRow,
)
from up_police_ai.db.session import create_db_session


def _make_officer_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def db_session():
    session = create_db_session()
    yield session
    session.rollback()
    session.close()


def test_officer_row_create_and_query(db_session):
    badge = f"TEST-{uuid.uuid4().hex[:8]}"
    officer = OfficerRow(name="Test Officer", badge_number=badge)
    db_session.add(officer)
    db_session.flush()

    fetched = db_session.query(OfficerRow).filter_by(badge_number=badge).first()
    assert fetched is not None
    assert fetched.name == "Test Officer"
    assert fetched.badge_number == badge
    assert fetched.id is not None


def test_assessment_row_create_and_query(db_session):
    badge = f"ASSESS-{uuid.uuid4().hex[:8]}"
    officer = OfficerRow(name="Assess Officer", badge_number=badge)
    db_session.add(officer)
    db_session.flush()

    assessment = AssessmentRow(
        officer_id=officer.id,
        score_a1=3.0, score_a2=3.0, score_a3=3.0, score_a4=3.0, score_a5=3.0,
        score_b1=4.0, score_b2=4.0, score_b3=4.0, score_b4=4.0, score_b5=4.0,
        score_c1=2.0, score_c2=2.0, score_c3=2.0, score_c4=2.0, score_c5=2.0,
        score_d1=5.0, score_d2=5.0, score_d3=5.0, score_d4=5.0, score_d5=5.0,
        avg_a=3.0,
        avg_b=4.0,
        avg_c=2.0,
        avg_d=5.0,
        avg_overall=3.5,
        completed_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(assessment)
    db_session.flush()

    fetched = db_session.query(AssessmentRow).filter_by(officer_id=officer.id).first()
    assert fetched is not None
    assert fetched.avg_a == 3.0
    assert fetched.avg_d == 5.0


def test_learning_plan_row_create_and_query(db_session):
    badge = f"PLAN-{uuid.uuid4().hex[:8]}"
    officer = OfficerRow(name="Plan Officer", badge_number=badge)
    db_session.add(officer)
    db_session.flush()

    assessment = AssessmentRow(
        officer_id=officer.id,
        score_a1=3.0, score_a2=3.0, score_a3=3.0, score_a4=3.0, score_a5=3.0,
        score_b1=3.0, score_b2=3.0, score_b3=3.0, score_b4=3.0, score_b5=3.0,
        score_c1=3.0, score_c2=3.0, score_c3=3.0, score_c4=3.0, score_c5=3.0,
        score_d1=3.0, score_d2=3.0, score_d3=3.0, score_d4=3.0, score_d5=3.0,
        avg_a=3.0, avg_b=3.0, avg_c=3.0, avg_d=3.0, avg_overall=3.0,
        completed_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(assessment)
    db_session.flush()

    plan = LearningPlanRow(officer_id=officer.id, assessment_id=assessment.id)
    db_session.add(plan)
    db_session.flush()

    fetched = db_session.query(LearningPlanRow).filter_by(officer_id=officer.id).first()
    assert fetched is not None
    assert fetched.assessment_id == assessment.id


def test_plan_day_row_create_and_query(db_session):
    badge = f"DAY-{uuid.uuid4().hex[:8]}"
    officer = OfficerRow(name="Day Officer", badge_number=badge)
    db_session.add(officer)
    db_session.flush()

    assessment = AssessmentRow(
        officer_id=officer.id,
        score_a1=2.0, score_a2=2.0, score_a3=2.0, score_a4=2.0, score_a5=2.0,
        score_b1=2.0, score_b2=2.0, score_b3=2.0, score_b4=2.0, score_b5=2.0,
        score_c1=2.0, score_c2=2.0, score_c3=2.0, score_c4=2.0, score_c5=2.0,
        score_d1=2.0, score_d2=2.0, score_d3=2.0, score_d4=2.0, score_d5=2.0,
        avg_a=2.0, avg_b=2.0, avg_c=2.0, avg_d=2.0, avg_overall=2.0,
        completed_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(assessment)
    db_session.flush()

    plan = LearningPlanRow(officer_id=officer.id, assessment_id=assessment.id)
    db_session.add(plan)
    db_session.flush()

    day = PlanDayRow(
        plan_id=plan.id,
        day_number=1,
        focus_area="AI Tools & General Literacy",
        level="Beginner",
        task_key="A_B_0",
        status="not_started",
    )
    db_session.add(day)
    db_session.flush()

    fetched = db_session.query(PlanDayRow).filter_by(plan_id=plan.id).first()
    assert fetched is not None
    assert fetched.day_number == 1
    assert fetched.task_key == "A_B_0"
    assert fetched.status == "not_started"


def test_plan_generator_creates_30_days():
    """Test the plan generator service creates exactly 30 days."""
    from up_police_ai.services.plan_generator import generate_plan_days

    plan_id = str(uuid.uuid4())
    days = generate_plan_days(
        plan_id=plan_id,
        avg_a=2.0,  # Beginner
        avg_b=3.0,  # Intermediate
        avg_c=4.0,  # Advanced
        avg_d=1.5,  # Beginner
    )
    assert len(days) == 30
    # Day 1: area A, beginner → A_B_0
    assert days[0].task_key == "A_B_0"
    # Day 2: area B, intermediate → B_I_0
    assert days[1].task_key == "B_I_0"
    # Day 3: area C, advanced → C_V_0
    assert days[2].task_key == "C_V_0"
    # Day 4: area D, beginner → D_B_0
    assert days[3].task_key == "D_B_0"
    # Day 5: area A, beginner, occurrence=1, task_idx=1 → A_B_1
    assert days[4].task_key == "A_B_1"
