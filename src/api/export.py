"""CSV export endpoint — download last query result as CSV."""
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from api._common import api_error
from db.models import SessionRow, MessageRow
from db.session import get_session

router = APIRouter()


@router.post("/sessions/{session_id}/export")
def export_result(session_id: str, db: Session = Depends(get_session)):
    """Download the last assistant message's result table as a CSV file."""
    session = db.get(SessionRow, session_id)
    if session is None:
        raise api_error("SESSION_NOT_FOUND", "Session not found", status_code=404)

    # Get the last assistant message that has an exportable CSV result
    stmt = (
        select(MessageRow)
        .where(MessageRow.session_id == session_id)
        .where(MessageRow.role == "assistant")
        .where(MessageRow.last_result_csv.is_not(None))
        .order_by(MessageRow.created_at.desc())
        .limit(1)
    )
    row = db.execute(stmt).scalars().first()

    if row is None or not row.last_result_csv:
        raise api_error("NO_RESULT", "No exportable result from the last query")

    csv_bytes = row.last_result_csv.encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=result.csv"},
    )
