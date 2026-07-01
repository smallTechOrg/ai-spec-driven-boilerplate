"""Session management endpoints."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.models import SessionRow
from db.session import get_session
from config.settings import get_settings

router = APIRouter()


@router.post("/sessions")
def create_session(db: Session = Depends(get_session)) -> dict:
    """Create a new analysis session."""
    row = SessionRow()
    db.add(row)
    db.flush()
    return ok({"session_id": row.id, "created_at": row.created_at.isoformat()})


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_session)) -> dict:
    """Delete session, all messages, all uploaded files, and temp files from disk."""
    row = db.get(SessionRow, session_id)
    if row is None:
        raise api_error("SESSION_NOT_FOUND", "Session not found", status_code=404)

    # Delete temp files from disk
    temp_session_dir: Path = get_settings().get_temp_dir() / session_id
    if temp_session_dir.exists():
        shutil.rmtree(temp_session_dir, ignore_errors=True)

    db.delete(row)
    return ok({"deleted": True})
