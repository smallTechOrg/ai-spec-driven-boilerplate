"""Chat message endpoints."""

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.models import SessionRow, UploadedFileRow, MessageRow
from db.session import get_session
from graph.runner import run_question

router = APIRouter()


class MessageRequest(BaseModel):
    content: str


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: str,
    body: MessageRequest,
    db: Session = Depends(get_session),
) -> dict:
    """Send a user question and receive an assistant answer."""
    # Validate session
    session = db.get(SessionRow, session_id)
    if session is None:
        raise api_error("SESSION_NOT_FOUND", "Session not found", status_code=404)

    # Check uploaded files
    stmt = select(UploadedFileRow).where(UploadedFileRow.session_id == session_id)
    file_rows = db.execute(stmt).scalars().all()
    if not file_rows:
        raise api_error("NO_FILES", "Upload a CSV file before asking questions")

    # Save user message
    user_msg = MessageRow(session_id=session_id, role="user", content=body.content)
    db.add(user_msg)
    db.flush()

    # Build uploaded_files list for the runner
    uploaded_files = []
    for row in file_rows:
        profile = row.profile_json
        if isinstance(profile, str):
            try:
                profile = json.loads(profile)
            except (json.JSONDecodeError, TypeError):
                profile = {}
        uploaded_files.append({
            "file_id": row.id,
            "filename": row.filename,
            "path": row.temp_path,
            "profile_json": profile,
        })

    # Run Q&A pipeline
    result = run_question(
        session_id=session_id,
        question=body.content,
        uploaded_files=uploaded_files,
    )

    answer = result.get("answer") or ""
    chart_json = result.get("chart_json")

    # Save assistant message
    assistant_msg = MessageRow(
        session_id=session_id,
        role="assistant",
        content=answer,
        chart_json=json.dumps(chart_json) if chart_json is not None else None,
    )
    db.add(assistant_msg)
    db.flush()
    message_id = assistant_msg.id

    return ok({
        "message_id": message_id,
        "role": "assistant",
        "content": answer,
        "chart_json": chart_json,
    })


@router.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: str,
    db: Session = Depends(get_session),
) -> dict:
    """Retrieve full conversation history for a session."""
    # Validate session
    session = db.get(SessionRow, session_id)
    if session is None:
        raise api_error("SESSION_NOT_FOUND", "Session not found", status_code=404)

    stmt = (
        select(MessageRow)
        .where(MessageRow.session_id == session_id)
        .order_by(MessageRow.created_at.asc())
    )
    rows = db.execute(stmt).scalars().all()

    messages = []
    for row in rows:
        chart = None
        if row.chart_json is not None:
            try:
                chart = json.loads(row.chart_json)
            except (json.JSONDecodeError, TypeError):
                chart = None

        messages.append({
            "message_id": row.id,
            "role": row.role,
            "content": row.content,
            "chart_json": chart,
            "created_at": row.created_at.isoformat(),
        })

    return ok({"messages": messages})
