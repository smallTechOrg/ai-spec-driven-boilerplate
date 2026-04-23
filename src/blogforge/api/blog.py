from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from blogforge.api.schemas import BlogIn
from blogforge.db.repository import get_blog, upsert_blog
from blogforge.db.session import get_session

router = APIRouter(prefix="/blog", tags=["blog"])


async def _db():
    async with get_session() as session:
        yield session


@router.get("")
async def read_blog(session: AsyncSession = Depends(_db)):
    blog = await get_blog(session)
    if blog is None:
        raise HTTPException(status_code=404, detail="Blog not configured")
    return blog.model_dump()


@router.put("")
async def update_blog(body: BlogIn, session: AsyncSession = Depends(_db)):
    fields = body.model_dump(exclude_none=True)
    if "posts_per_run" in fields and not (1 <= fields["posts_per_run"] <= 10):
        raise HTTPException(status_code=422, detail="posts_per_run must be 1–10")
    if "schedule_cron" in fields and fields["schedule_cron"]:
        try:
            from croniter import croniter
            if not croniter.is_valid(fields["schedule_cron"]):
                raise ValueError()
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid cron expression")
    blog = await upsert_blog(session, **fields)
    return blog.model_dump()
