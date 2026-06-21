"""JSON API — the contract the Next.js chat UI calls.

POST /api/run  body: {"input": "<text>"}
              ->  {"ok": true, "data": {"result": "<string>", "run_id": <id>}}

Drives the agent graph, persists ONE Run row through the DB layer (so the
persistence seam is demonstrably live), and returns the result. This is the full
generic vertical slice: UI -> API -> graph -> echo tool -> stub LLM ->
SQLite persistence -> response.
"""

from fastapi import APIRouter
from pydantic import BaseModel

import src.db.session as db_session
from src.agent.graph import graph
from src.agent.state import AgentState
from src.db.models import Run

router = APIRouter(prefix="/api")


class RunRequest(BaseModel):
    input: str


async def run_agent(user_input: str) -> tuple[str, int | None, str | None]:
    """Run the graph and persist a Run row. Returns (result, run_id, error)."""
    state: AgentState = {
        "run_id": 0,
        "user_input": user_input,
        "tool_call_history": [],
        "result": None,
        "error": None,
        "iterations": 0,
    }
    final = await graph.ainvoke(state)
    error = final.get("error")
    result = final.get("result") or ""

    # Persist one Run row through the DB layer (closes the persistence loop).
    # Reference the module attribute so tests can swap AsyncSessionLocal.
    run_id: int | None = None
    if db_session.AsyncSessionLocal is not None:
        async with db_session.AsyncSessionLocal() as session:
            row = Run(input=user_input, result=None if error else result)
            session.add(row)
            await session.commit()
            run_id = row.id

    return result, run_id, error


@router.post("/run")
async def run(req: RunRequest) -> dict:
    user_input = req.input.strip()
    if not user_input:
        return {"ok": False, "error": "Empty input."}
    result, run_id, error = await run_agent(user_input)
    if error:
        return {"ok": False, "error": error}
    return {"ok": True, "data": {"result": result, "run_id": run_id}}
