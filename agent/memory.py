"""Long-term, cross-session memory: durable facts the agent recalls in any later session.
Distinct from short-term memory (the session document + in-thread message history)."""
from sqlalchemy import desc, select
from .db import Memory, get_sessionmaker


async def remember(content: str) -> str:
    """Store a durable fact. Persists across sessions; released only on explicit delete."""
    content = (content or "").strip()
    if not content:
        return "nothing to remember"
    async with get_sessionmaker()() as s:
        s.add(Memory(content=content))
        await s.commit()
    return content


async def recall(limit: int = 20) -> list[str]:
    """The most recent durable facts (newest first)."""
    async with get_sessionmaker()() as s:
        rows = (await s.execute(
            select(Memory).order_by(desc(Memory.created_at)).limit(limit))).scalars().all()
    return [r.content for r in rows]


async def recall_text(limit: int = 20) -> str:
    return "\n".join(f"- {f}" for f in await recall(limit))
