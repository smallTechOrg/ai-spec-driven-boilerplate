from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from api._common import api_error
from db.session import create_db_session
from db.models import SessionRow

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/")
def chat(
    session_id: str = Query(...),
    q: str = Query(...),
):
    # Validate question is not blank before opening stream
    if not q.strip():
        raise api_error("INVALID_QUESTION", "Question cannot be blank", 400)

    # Validate session exists before opening stream
    with create_db_session() as db:
        session = db.get(SessionRow, session_id)
        if session is None:
            raise api_error("SESSION_NOT_FOUND", f"Session {session_id!r} not found", 404)

    from graph.runner import run_analyst

    def generate():
        yield from run_analyst(session_id, q.strip())

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
