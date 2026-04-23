import asyncio
import logging
import re
from datetime import datetime, timezone

import markdown
from google import genai
from google.genai import types

from blogforge.config import settings
from blogforge.domain.models import Writer

logger = logging.getLogger(__name__)

_USER_PROMPT = """\
Write a blog post for "{blog_name}" (niche: {niche}) on the topic: "{topic}"

Requirements:
- Writer voice: follow the system prompt persona exactly
- Length: 800–1500 words
- Structure: an engaging introduction, at least 3 ## subheadings, and a conclusion
- Tone: informative but conversational
- Output: Markdown only — title as # heading, then body. No preamble, no explanations.
"""


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9\s-]", "", title.lower())
    slug = re.sub(r"\s+", "-", slug.strip())
    suffix = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"{slug[:60]}-{suffix}"


def _extract_title(content_md: str, fallback: str) -> tuple[str, str]:
    lines = content_md.strip().splitlines()
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        body = "\n".join(lines[1:]).strip()
        return title, body
    return fallback, content_md


def _call_gemini(writer_prompt: str, user_prompt: str) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=writer_prompt),
    )
    return response.text.strip()


async def generate_post(topic: str, writer: Writer, blog_name: str, blog_niche: str) -> dict:
    prompt = _USER_PROMPT.format(blog_name=blog_name, niche=blog_niche, topic=topic)

    for attempt in (1, 2):
        try:
            content_md = await asyncio.to_thread(_call_gemini, writer.persona_prompt, prompt)
            title, body = _extract_title(content_md, topic)
            full_md = f"# {title}\n\n{body}"
            content_html = markdown.markdown(full_md, extensions=["extra"])
            logger.info("post_generation.ok", extra={"topic": topic, "attempt": attempt})
            return {
                "title": title,
                "slug": _slugify(title),
                "content_markdown": full_md,
                "content_html": content_html,
            }
        except Exception as exc:
            logger.warning("post_generation.retry", extra={"topic": topic, "attempt": attempt, "error": str(exc)})
            if attempt == 2:
                raise
            await asyncio.sleep(2)
