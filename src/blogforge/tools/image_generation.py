import asyncio
import logging
from pathlib import Path

import aiofiles

from blogforge.config import settings

logger = logging.getLogger(__name__)

SVG_PLACEHOLDER = """\
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#4f46e5;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#7c3aed;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#g)" />
  <text x="600" y="315" font-family="sans-serif" font-size="48" fill="white"
        text-anchor="middle" dominant-baseline="middle">{title}</text>
</svg>
"""


async def generate_image(post_id: int, title: str) -> str:
    """Stub: writes an SVG placeholder and returns its path."""
    await asyncio.sleep(0)
    images_dir = Path(settings.images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)
    path = images_dir / f"post-{post_id}-cover.svg"
    content = SVG_PLACEHOLDER.format(title=title[:40])
    async with aiofiles.open(path, "w") as f:
        await f.write(content)
    logger.info("image_generation.stub", extra={"post_id": post_id, "path": str(path)})
    return str(path)
