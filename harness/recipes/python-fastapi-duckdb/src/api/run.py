"""run_agent — drive one run end-to-end and close the persistence loop.

Invokes the LangGraph ReAct graph, persists ONE Run row through the SQLite spine,
and writes one event through the DuckDB columnar seam (the storage layer that makes
this recipe differ from python-fastapi-sqlite). Returns (result, run_id).
"""

from sqlalchemy import select

import src.db.session as db_session
from src.agent.graph import graph
from src.agent.state import AgentState
from src.db.duck import append_event
from src.db.models import Run


async def run_agent(user_input: str) -> tuple[str, int]:
    state: AgentState = {
        "run_id": 0,
        "user_input": user_input,
        "tool_call_history": [],
        "result": None,
        "error": None,
        "iterations": 0,
    }
    final = await graph.ainvoke(state)
    if final.get("error"):
        raise RuntimeError(final["error"])

    result = final.get("result") or ""

    # Persist ONE Run row through the DB layer (closes the persistence loop).
    async with db_session.AsyncSessionLocal() as session:
        run = Run(input=user_input, result=result)
        session.add(run)
        await session.commit()
        run_id = (await session.execute(select(Run.id).order_by(Run.id.desc()))).scalars().first()

    # Demonstrate the DuckDB storage seam: write the echo through the event store.
    append_event(kind="run", payload=result)

    return result, run_id
