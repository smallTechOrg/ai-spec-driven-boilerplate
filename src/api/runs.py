from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api._common import api_error, ok
from api._serializers import run_body
from db.models import AnalysisRun
from db.session import get_session

router = APIRouter()


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise api_error("NOT_FOUND", f"Run {run_id} not found", 404)
    return ok({"run": run_body(run)})
