import asyncio
import logging
from pathlib import Path

import aiofiles
from google import genai

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
  <text x="600" y="315" font-family="sans-serif" font-size="40" fill="white"
        text-anchor="middle" dominant-baseline="middle">{title}</text>
</svg>
"""


async def _write_svg(path: Path, title: str) -> None:
    async with aiofiles.open(path, "w") as f:
        await f.write(SVG_PLACEHOLDER.format(title=title[:60]))


def _generate_png(prompt: str) -> bytes:
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config={"number_of_images": 1, "aspect_ratio": "16:9"},
    )
    return response.generated_images[0].image.image_bytes


async def generate_image(post_id: int, title: str) -> str:
    images_dir = settings.images_path()
    png_path = images_dir / f"post-{post_id}-cover.png"
    svg_path = images_dir / f"post-{post_id}-cover.svg"

    try:
        prompt = f"Blog cover image for article titled '{title}'. Professional, modern, 1200x630, no text."
        image_bytes = await asyncio.to_thread(_generate_png, prompt)
        async with aiofiles.open(png_path, "wb") as f:
            await f.write(image_bytes)
        logger.info("image_generation.ok", extra={"post_id": post_id, "path": str(png_path)})
        return str(png_path)
    except Exception as exc:
        logger.warning("image_generation.fallback", extra={"post_id": post_id, "error": str(exc)})
        await _write_svg(svg_path, title)
        return str(svg_path)
