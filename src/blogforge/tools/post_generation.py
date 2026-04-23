import asyncio
import logging
import re
from datetime import datetime, timezone

from blogforge.domain.models import Writer

logger = logging.getLogger(__name__)

STUB_CONTENT = """\
# {title}

This is a stub post generated for testing purposes.

## Introduction

Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Main Point One

Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Main Point Two

Ut enim ad minim veniam, quis nostrud exercitation ullamco.

## Main Point Three

Duis aute irure dolor in reprehenderit in voluptate velit esse.

## Conclusion

Thank you for reading this stub post.
"""


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    suffix = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"{slug[:60]}-{suffix}"


async def generate_post(topic: str, writer: Writer, blog_name: str, blog_niche: str) -> dict:
    """Stub: returns hardcoded Markdown post."""
    await asyncio.sleep(0)
    title = topic
    content_md = STUB_CONTENT.format(title=title)
    logger.info("post_generation.stub", extra={"topic": topic, "writer_id": writer.id})
    return {
        "title": title,
        "slug": _slugify(title),
        "content_markdown": content_md,
        "content_html": f"<h1>{title}</h1><p>Stub content.</p>",
    }
