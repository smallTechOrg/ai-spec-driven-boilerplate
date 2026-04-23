from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from blogforge.api.schemas import WriterIn, WriterUpdate
from blogforge.db.repository import create_writer, deactivate_writer, get_writer, get_writers, update_writer
from blogforge.db.session import get_session

router = APIRouter(prefix="/writers", tags=["writers"])


async def _db():
    async with get_session() as session:
        yield session


@router.get("")
async def list_writers(session: AsyncSession = Depends(_db)):
    writers = await get_writers(session)
    return {"writers": [w.model_dump() for w in writers]}


@router.post("", status_code=201)
async def create(body: WriterIn, session: AsyncSession = Depends(_db)):
    writer = await create_writer(session, name=body.name, persona_prompt=body.persona_prompt,
                                  bio=body.bio, avatar_url=body.avatar_url)
    return writer.model_dump()


@router.put("/{writer_id}")
async def update(writer_id: int, body: WriterUpdate, session: AsyncSession = Depends(_db)):
    fields = body.model_dump(exclude_none=True)
    writer = await update_writer(session, writer_id, **fields)
    if writer is None:
        raise HTTPException(status_code=404, detail="Writer not found")
    return writer.model_dump()


@router.delete("/{writer_id}", status_code=204)
async def deactivate(writer_id: int, session: AsyncSession = Depends(_db)):
    ok = await deactivate_writer(session, writer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Writer not found")
