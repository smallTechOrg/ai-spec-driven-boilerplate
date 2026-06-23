from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from api._common import ok, api_error
from db.session import get_session
from db.models import SessionRow, DatasetRow, MessageRow

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", status_code=201)
def create_session(session: Session = Depends(get_session)) -> dict:
    count = session.scalar(select(func.count()).select_from(SessionRow)) or 0
    row = SessionRow(name=f"Session {count + 1}")
    session.add(row)
    session.flush()
    return ok({
        "session_id": row.id,
        "name": row.name,
        "created_at": row.created_at.isoformat(),
    })


@router.get("/", status_code=200)
def list_sessions(session: Session = Depends(get_session)) -> dict:
    rows = session.scalars(
        select(SessionRow).order_by(SessionRow.created_at.desc())
    ).all()

    result = []
    for row in rows:
        dataset_count = session.scalar(
            select(func.count()).select_from(DatasetRow)
            .where(DatasetRow.session_id == row.id)
        ) or 0
        message_count = session.scalar(
            select(func.count()).select_from(MessageRow)
            .where(MessageRow.session_id == row.id)
        ) or 0
        result.append({
            "session_id": row.id,
            "name": row.name,
            "created_at": row.created_at.isoformat(),
            "dataset_count": dataset_count,
            "message_count": message_count,
        })

    return ok(result)


@router.get("/{session_id}", status_code=200)
def get_session_detail(session_id: str, session: Session = Depends(get_session)) -> dict:
    import json

    row = session.get(SessionRow, session_id)
    if row is None:
        raise api_error("SESSION_NOT_FOUND", f"Session {session_id!r} not found", 404)

    datasets = session.scalars(
        select(DatasetRow).where(DatasetRow.session_id == session_id)
    ).all()

    messages = session.scalars(
        select(MessageRow)
        .where(MessageRow.session_id == session_id)
        .order_by(MessageRow.created_at.desc())
        .limit(50)
    ).all()
    # Return messages chronologically (oldest first) after fetching newest-50
    messages = list(reversed(messages))

    datasets_out = []
    for ds in datasets:
        try:
            columns = json.loads(ds.columns_json)
        except Exception:
            columns = []
        datasets_out.append({
            "dataset_id": ds.id,
            "name": ds.name,
            "row_count": ds.row_count,
            "columns": columns,
            "uploaded_at": ds.uploaded_at.isoformat(),
        })

    messages_out = []
    for msg in messages:
        entry = {
            "message_id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        if msg.role == "assistant":
            entry["status"] = msg.status
        messages_out.append(entry)

    return ok({
        "session_id": row.id,
        "name": row.name,
        "created_at": row.created_at.isoformat(),
        "datasets": datasets_out,
        "messages": messages_out,
    })


@router.patch("/{session_id}", status_code=501)
def rename_session(session_id: str) -> dict:
    raise api_error("NOT_IMPLEMENTED", "Coming in Phase 2", 501)


@router.delete("/{session_id}", status_code=501)
def delete_session(session_id: str) -> dict:
    raise api_error("NOT_IMPLEMENTED", "Coming in Phase 2", 501)
