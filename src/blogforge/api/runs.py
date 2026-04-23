import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from blogforge.api.schemas import TriggerIn
from blogforge.db.repository import get_active_run, get_blog, get_posts_for_run, get_run, get_runs, get_writers
from blogforge.db.session import get_session

router = APIRouter(prefix="/runs", tags=["runs"])


async def _db():
    async with get_session() as session:
        yield session


@router.get("")
async def list_runs(session: AsyncSession = Depends(_db)):
    runs = await get_runs(session)
    return {"runs": [r.model_dump() for r in runs]}


@router.get("/{run_id}")
async def get_run_detail(run_id: int, session: AsyncSession = Depends(_db)):
    run = await get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    posts = await get_posts_for_run(session, run_id)
    data = run.model_dump()
    data["posts"] = [p.model_dump() for p in posts]
    return data


@router.post("/trigger")
async def trigger_run(body: TriggerIn, background_tasks: BackgroundTasks,
                      session: AsyncSession = Depends(_db)):
    active = await get_active_run(session)
    if active:
        raise HTTPException(status_code=409, detail="A run is already in progress")

    blog = await get_blog(session)
    if blog is None or not blog.niche:
        raise HTTPException(status_code=422, detail="Blog not configured")

    writers = await get_writers(session)
    if not any(w.is_active for w in writers):
        raise HTTPException(status_code=422, detail="No active writers configured")

    posts_count = body.posts_count or (blog.posts_per_run if blog else 3)

    from blogforge.agent.runner import run_agent
    background_tasks.add_task(run_agent, trigger="manual", posts_count=posts_count)

    return {"status": "running", "posts_requested": posts_count}
