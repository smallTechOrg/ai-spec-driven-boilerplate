from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from api._common import ok, api_error
from db.session import get_session
from db.models import SessionRow, QueryLogRow

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/", status_code=200)
def list_audit_log(
    session_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict:
    # Validate session exists
    sess_row = session.get(SessionRow, session_id)
    if sess_row is None:
        raise api_error("SESSION_NOT_FOUND", f"Session {session_id!r} not found", 404)

    total = session.scalar(
        select(func.count()).select_from(QueryLogRow)
        .where(QueryLogRow.session_id == session_id)
    ) or 0

    rows = session.scalars(
        select(QueryLogRow)
        .where(QueryLogRow.session_id == session_id)
        .order_by(QueryLogRow.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    entries = [
        {
            "query_log_id": ql.id,
            "dataset_name": ql.dataset_name,
            "sql": ql.sql,
            "row_count": ql.row_count,
            "latency_ms": ql.latency_ms,
            "error": ql.error,
            "created_at": ql.created_at.isoformat(),
        }
        for ql in rows
    ]

    return ok({"total": total, "entries": entries})
