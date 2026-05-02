from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from up_police_ai.api._common import render
from up_police_ai.data.tasks import TASKS
from up_police_ai.db.models import AssessmentRow, LearningPlanRow, OfficerRow, PlanDayRow
from up_police_ai.db.session import get_session

router = APIRouter()


def _require_officer(request: Request, session: Session) -> OfficerRow | None:
    officer_id = request.session.get("officer_id")
    if not officer_id:
        return None
    return session.query(OfficerRow).filter_by(id=officer_id).first()


@router.get("/plan")
async def plan_view(request: Request, session: Session = Depends(get_session)):
    officer = _require_officer(request, session)
    if officer is None:
        return RedirectResponse(url="/", status_code=302)

    plan = session.query(LearningPlanRow).filter_by(officer_id=officer.id).first()
    if plan is None:
        return RedirectResponse(url="/assessment", status_code=302)

    assessment = session.query(AssessmentRow).filter_by(officer_id=officer.id).first()
    days = (
        session.query(PlanDayRow)
        .filter_by(plan_id=plan.id)
        .order_by(PlanDayRow.day_number)
        .all()
    )

    # Attach task details to each day for rendering
    days_with_tasks = []
    for day in days:
        task_detail = TASKS.get(day.task_key, {})
        days_with_tasks.append({
            "id": day.id,
            "day_number": day.day_number,
            "focus_area": day.focus_area,
            "level": day.level,
            "task_key": day.task_key,
            "task": task_detail.get("task", ""),
            "resource": task_detail.get("resource", ""),
            "minutes": task_detail.get("minutes", 0),
            "status": day.status,
            "completed_at": day.completed_at,
        })

    done_count = sum(1 for d in days if d.status == "done")

    return render(
        request,
        "plan.html",
        officer=officer,
        plan=plan,
        assessment=assessment,
        days=days_with_tasks,
        done_count=done_count,
        total_days=len(days),
    )


@router.post("/plan/day/{day_id}/status")
async def update_day_status(
    day_id: str,
    request: Request,
    status: str = Form(...),
    session: Session = Depends(get_session),
):
    officer = _require_officer(request, session)
    if officer is None:
        return RedirectResponse(url="/", status_code=302)

    day = session.query(PlanDayRow).filter_by(id=day_id).first()
    if day is None:
        return RedirectResponse(url="/plan", status_code=302)

    # Verify the day belongs to this officer's plan
    plan = session.query(LearningPlanRow).filter_by(
        id=day.plan_id, officer_id=officer.id
    ).first()
    if plan is None:
        return RedirectResponse(url="/plan", status_code=302)

    day.status = status
    if status == "done":
        day.completed_at = datetime.now(tz=timezone.utc)
    else:
        day.completed_at = None

    return RedirectResponse(url="/plan", status_code=302)
