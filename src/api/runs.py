import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.session import get_session
from db.models import RunRow
from domain.run import RunRequest, RunResponse

router = APIRouter()


@router.post("/runs")
def create_run(req: RunRequest, session: Session = Depends(get_session)) -> dict:
    """Deprecated: use POST /sessions/{session_id}/queries instead."""
    raise api_error(
        "DEPRECATED",
        "POST /runs is deprecated. Use POST /sessions to create a session, "
        "POST /sessions/{session_id}/datasets to upload a CSV, "
        "then POST /sessions/{session_id}/queries to run a query.",
        400,
    )


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    run = session.get(RunRow, run_id)
    if run is None:
        raise api_error("NOT_FOUND", f"Run {run_id} not found", 404)
    table_data = None
    if run.table_json:
        try:
            table_data = json.loads(run.table_json)
        except (ValueError, TypeError):
            table_data = None
    return ok(RunResponse(
        run_id=run.id,
        status=run.status,
        output_text=run.output_text,
        answer_text=run.answer_text,
        table_data=table_data,
        chart_b64=run.chart_b64,
        error=run.error_message,
    ).model_dump())
