import asyncio
import logging

from google import genai

from blogforge.config import settings

logger = logging.getLogger(__name__)

_SELECTION_PROMPT = """\
You are a blog topic curator for a "{niche}" blog.

Theme areas to cover: {themes}

Candidate topics gathered from web search and brainstorming:
{candidates}

Previously used topics (NEVER repeat these):
{used}

From the candidates, select exactly {count} topics that are:
- Fresh and not in the used list (case-insensitive)
- Relevant to the niche and at least one theme area
- Specific enough to write a focused 1000-word post about
- Distinct from each other

Return ONLY a numbered list of topic titles, one per line, nothing else.
"""


def _ddg_search(query: str, max_results: int = 10) -> list[str]:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
        return [r.get("title", "") for r in results if r.get("title")]
    except Exception as exc:
        logger.warning("ddg.failed", extra={"error": str(exc)})
        return []


def _tavily_search(query: str, max_results: int = 10) -> list[str]:
    if not settings.tavily_api_key:
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        results = client.search(query, max_results=max_results)
        return [r.get("title", "") for r in results.get("results", []) if r.get("title")]
    except Exception as exc:
        logger.warning("tavily.failed", extra={"error": str(exc)})
        return []


def _gemini_select(prompt: str) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text.strip()


async def discover_topics(niche: str, themes: list[str], used_topics: list[str], count: int = 5) -> list[str]:
    query = f"{niche} {' '.join(themes[:2])} tips trends 2024"

    ddg_titles, tavily_titles = await asyncio.gather(
        asyncio.to_thread(_ddg_search, query),
        asyncio.to_thread(_tavily_search, query),
    )

    seen: set[str] = set()
    candidates: list[str] = []
    for title in ddg_titles + tavily_titles:
        t = title.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            candidates.append(t)

    used_lower = {u.lower() for u in used_topics}
    candidates = [c for c in candidates if c.lower() not in used_lower]

    if not candidates:
        candidates = [
            f"Best {niche} practices for beginners",
            f"Advanced {niche} strategies that actually work",
            f"Common {niche} mistakes to avoid in {themes[0] if themes else 'your work'}",
            f"How to get started with {niche}",
            f"The future of {niche}: what to expect",
        ]

    prompt = _SELECTION_PROMPT.format(
        niche=niche,
        themes=", ".join(themes) if themes else niche,
        candidates="\n".join(f"- {c}" for c in candidates[:30]),
        used="\n".join(f"- {u}" for u in used_topics[:50]) or "None",
        count=count,
    )

    try:
        text = await asyncio.to_thread(_gemini_select, prompt)
        topics = []
        for line in text.splitlines():
            topic = line.lstrip("0123456789.-) ").strip()
            if topic and topic.lower() not in used_lower:
                topics.append(topic)
        logger.info("topic_discovery.ok", extra={"niche": niche, "found": len(topics)})
        return topics[:count]
    except Exception as exc:
        logger.warning("topic_discovery.gemini_failed", extra={"error": str(exc)})
        return [c for c in candidates[:count] if c.lower() not in used_lower]
