import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from up_police_ai.api._common import render
from up_police_ai.data.tasks import SECTION_QUESTIONS
from up_police_ai.db.models import AssessmentRow, LearningPlanRow, OfficerRow
from up_police_ai.db.session import get_session
from up_police_ai.services.plan_generator import generate_plan_days

router = APIRouter()


def _require_officer(request: Request, session: Session) -> OfficerRow | None:
    officer_id = request.session.get("officer_id")
    if not officer_id:
        return None
    return session.query(OfficerRow).filter_by(id=officer_id).first()


@router.get("/assessment")
async def assessment_form(request: Request, session: Session = Depends(get_session)):
    officer = _require_officer(request, session)
    if officer is None:
        return RedirectResponse(url="/", status_code=302)
    return render(request, "assessment.html", questions=SECTION_QUESTIONS, officer=officer)


@router.post("/assessment")
async def assessment_submit(
    request: Request,
    session: Session = Depends(get_session),
    a1: float = Form(...),
    a2: float = Form(...),
    a3: float = Form(...),
    a4: float = Form(...),
    a5: float = Form(...),
    b1: float = Form(...),
    b2: float = Form(...),
    b3: float = Form(...),
    b4: float = Form(...),
    b5: float = Form(...),
    c1: float = Form(...),
    c2: float = Form(...),
    c3: float = Form(...),
    c4: float = Form(...),
    c5: float = Form(...),
    d1: float = Form(...),
    d2: float = Form(...),
    d3: float = Form(...),
    d4: float = Form(...),
    d5: float = Form(...),
):
    officer = _require_officer(request, session)
    if officer is None:
        return RedirectResponse(url="/", status_code=302)

    avg_a = (a1 + a2 + a3 + a4 + a5) / 5
    avg_b = (b1 + b2 + b3 + b4 + b5) / 5
    avg_c = (c1 + c2 + c3 + c4 + c5) / 5
    avg_d = (d1 + d2 + d3 + d4 + d5) / 5
    avg_overall = (avg_a + avg_b + avg_c + avg_d) / 4

    assessment = AssessmentRow(
        officer_id=officer.id,
        score_a1=a1, score_a2=a2, score_a3=a3, score_a4=a4, score_a5=a5,
        score_b1=b1, score_b2=b2, score_b3=b3, score_b4=b4, score_b5=b5,
        score_c1=c1, score_c2=c2, score_c3=c3, score_c4=c4, score_c5=c5,
        score_d1=d1, score_d2=d2, score_d3=d3, score_d4=d4, score_d5=d5,
        avg_a=avg_a, avg_b=avg_b, avg_c=avg_c, avg_d=avg_d, avg_overall=avg_overall,
        completed_at=datetime.now(tz=timezone.utc),
    )
    session.add(assessment)
    session.flush()

    plan = LearningPlanRow(
        officer_id=officer.id,
        assessment_id=assessment.id,
    )
    session.add(plan)
    session.flush()

    days = generate_plan_days(
        plan_id=plan.id,
        avg_a=avg_a,
        avg_b=avg_b,
        avg_c=avg_c,
        avg_d=avg_d,
    )
    for day in days:
        session.add(day)

    return RedirectResponse(url="/plan", status_code=302)
