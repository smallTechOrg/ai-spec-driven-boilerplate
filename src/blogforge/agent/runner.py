import logging

from blogforge.agent.graph import graph
from blogforge.agent.state import GenerationState
from blogforge.db.repository import create_run, get_blog, get_writers
from blogforge.db.session import get_session

logger = logging.getLogger(__name__)


async def run_agent(trigger: str = "manual", posts_count: int = 3) -> int:
    """Create a run record and execute the generation graph. Returns run_id."""
    async with get_session() as session:
        blog = await get_blog(session)
        if blog is None:
            raise ValueError("Blog not configured — set name and niche before running")
        writers = await get_writers(session)
        if not any(w.is_active for w in writers):
            raise ValueError("No active writers — add at least one writer before running")
        run = await create_run(session, trigger=trigger, posts_requested=posts_count)

    initial_state: GenerationState = {
        "run_id": run.id,
        "blog": blog,
        "posts_count": posts_count,
        "topics": [],
        "assignments": [],
        "completed_posts": [],
        "failed_topics": [],
        "error": None,
    }

    logger.info("agent.start", extra={"run_id": run.id, "trigger": trigger})
    await graph.ainvoke(initial_state)
    logger.info("agent.done", extra={"run_id": run.id})
    return run.id
