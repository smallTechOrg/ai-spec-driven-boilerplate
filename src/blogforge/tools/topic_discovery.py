import asyncio
import logging

logger = logging.getLogger(__name__)

STUB_TOPICS = [
    "How to Start a Morning Routine That Actually Sticks",
    "The Case for Analog Note-Taking in a Digital World",
    "Why Deep Work Is the Skill of the Decade",
]


async def discover_topics(niche: str, themes: list[str], used_topics: list[str]) -> list[str]:
    """Stub: returns hardcoded topics ignoring all inputs."""
    await asyncio.sleep(0)
    logger.info("topic_discovery.stub", extra={"niche": niche, "count": len(STUB_TOPICS)})
    return [t for t in STUB_TOPICS if t.lower() not in {u.lower() for u in used_topics}]
