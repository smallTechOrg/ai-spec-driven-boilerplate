import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from datachat.api._common import api_error
from datachat.db.models import SessionRow, MessageRow
from datachat.db.session import get_session

router = APIRouter(prefix="/api")


class QuestionRequest(BaseModel):
    question: str


@router.post("/sessions/{session_id}/messages/stream")
async def ask_question_stream(
    session_id: str,
    body: QuestionRequest,
    db: Session = Depends(get_session),
):
    row = db.get(SessionRow, session_id)
    if not row:
        raise api_error("NOT_FOUND", f"Session {session_id} not found", 404)
    if row.status != "ready":
        raise api_error("SESSION_NOT_READY", f"Session status is {row.status}", 400)

    from datachat.graph.nodes import _dataframe_store
    df = _dataframe_store.get(session_id)
    if df is None:
        raise api_error(
            "SESSION_DATA_LOST",
            "Session data is no longer in memory — please re-upload your file",
            410,
        )

    user_msg = MessageRow(session_id=session_id, role="user", content=body.question)
    db.add(user_msg)
    db.commit()

    from datachat.graph.runner import iter_agent_events

    async def _generate():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run_sync():
            try:
                for event in iter_agent_events(session_id, body.question, df):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = loop.run_in_executor(executor, _run_sync)
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
            await future

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
