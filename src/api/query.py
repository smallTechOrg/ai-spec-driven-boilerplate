import json

from fastapi import APIRouter
from pydantic import BaseModel

from src.agent.graph import analyst_graph
from src.db.connection import get_db
from src.sessions.manager import ensure_session, load_history, save_message

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


@router.post("/")
async def query(req: QueryRequest):
    conn = get_db()
    try:
        # Ensure session exists
        ensure_session(conn, req.session_id)

        # Load conversation history
        history = load_history(conn, req.session_id)

        # Save user message
        save_message(conn, req.session_id, "user", req.question)

        # Get registered datasets
        rows = conn.execute("SELECT name FROM datasets").fetchall()
        datasets = [r[0] for r in rows]
    finally:
        conn.close()

    result = analyst_graph.invoke(
        {
            "question": req.question,
            "session_id": req.session_id,
            "datasets": datasets,
            "history": history,
            "plan": "",
            "sql": "",
            "intent": "table",
            "x_col": "",
            "y_col": "",
            "raw_rows": [],
            "columns": [],
            "response": {},
        }
    )

    # Save assistant response summary to history
    response = result["response"]
    summary = response.get(
        "markdown", json.dumps(response.get("plotly_spec", {}))[:200]
    )
    conn2 = get_db()
    try:
        save_message(conn2, req.session_id, "assistant", summary)
    finally:
        conn2.close()

    return response
