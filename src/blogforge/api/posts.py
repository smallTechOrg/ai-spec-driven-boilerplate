from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from blogforge.db.repository import get_posts
from blogforge.db.session import get_session

router = APIRouter(prefix="/posts", tags=["posts"])


async def _db():
    async with get_session() as session:
        yield session


@router.get("")
async def list_posts(limit: int = 20, offset: int = 0, writer_id: int | None = None,
                     session: AsyncSession = Depends(_db)):
    posts = await get_posts(session, writer_id=writer_id, limit=limit, offset=offset)
    return {"posts": [p.model_dump() for p in posts]}
