from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from up_police_ai.api._common import render
from up_police_ai.db.models import OfficerRow, AssessmentRow
from up_police_ai.db.session import get_session

router = APIRouter()


def _get_officer(request: Request, session: Session) -> OfficerRow | None:
    officer_id = request.session.get("officer_id")
    if not officer_id:
        return None
    return session.query(OfficerRow).filter_by(id=officer_id).first()


@router.get("/")
async def index(request: Request, session: Session = Depends(get_session)):
    officer_id = request.session.get("officer_id")
    if officer_id:
        officer = session.query(OfficerRow).filter_by(id=officer_id).first()
        if officer:
            return RedirectResponse(url="/plan", status_code=302)
    return render(request, "index.html")


@router.get("/register")
async def register_form(request: Request):
    return render(request, "register.html")


@router.post("/register")
async def register_submit(
    request: Request,
    name: str = Form(...),
    badge_number: str = Form(...),
    session: Session = Depends(get_session),
):
    badge_number = badge_number.strip()
    name = name.strip()

    # Check if officer already exists by badge number
    officer = session.query(OfficerRow).filter_by(badge_number=badge_number).first()
    if officer is None:
        # Create new officer
        officer = OfficerRow(name=name, badge_number=badge_number)
        session.add(officer)
        session.flush()

    # Set session
    request.session["officer_id"] = officer.id

    # Check if assessment already exists
    has_assessment = (
        session.query(AssessmentRow).filter_by(officer_id=officer.id).first()
        is not None
    )
    if has_assessment:
        return RedirectResponse(url="/plan", status_code=302)
    return RedirectResponse(url="/assessment", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
