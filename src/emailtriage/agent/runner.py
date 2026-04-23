from emailtriage.agent.graph import graph
from emailtriage.db.repository import create_run
from emailtriage.db.session import get_session, init_db

async def run_agent() -> int:
    await init_db()
    async with get_session() as session:
        run = await create_run(session)
    await graph.ainvoke({"run_id": run.id, "emails": [], "results": [], "error": None})
    return run.id
