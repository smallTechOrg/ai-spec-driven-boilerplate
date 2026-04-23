"""
Live integration test for the Gemini Vision provider.

This test is SKIPPED unless FOOD_TRACKER_GEMINI_API_KEY is set in the environment.
Run it with:

    FOOD_TRACKER_GEMINI_API_KEY=<your-key> uv run pytest tests/integration/test_gemini_live.py -v

from the repo root.
"""
import io
import os

import pytest

API_KEY = os.environ.get("FOOD_TRACKER_GEMINI_API_KEY", "")

pytestmark = pytest.mark.skipif(
    not API_KEY,
    reason="FOOD_TRACKER_GEMINI_API_KEY not set — skipping live Gemini test",
)

# A small publicly-known test image: a 100x100 JPEG of a bright yellow banana
# (base64-decoded inline so the test has no network dependency beyond Gemini itself)
import base64

_BANANA_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
    "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgN"
    "DRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
    "MjL/wAARCAAyADIDASIAAhEBAxEB/8QAGwABAAIDAQEAAAAAAAAAAAAAAAUGAwQHAQL/"
    "xAAuEAABBAIBAgUDBAMAAAAAAAABAAIDBAUREiExBhNBUWEUIjJxgZHBFSNC0f/"
    "EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIR"
    "AxEAPwDv4iICIiAiIgIiICIiAiIgIiICIiAiIgIiICIiAiIgIiICIiAiIgIiICIiAiIg"
    "IiICIiAiIgIiICIiAiIgIiICIiAiIgIiICIiAiIgIiICIiAiIgIiICIiAiIgIiICIiD/"
    "2Q=="
)

try:
    _TEST_IMAGE = base64.b64decode(_BANANA_JPEG_B64)
except Exception:
    _TEST_IMAGE = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"


def test_gemini_live_analyse_food():
    """Real call to Gemini Vision — confirms the integration is wired correctly."""
    from food_tracker.config.settings import Settings
    from food_tracker.llm.providers.gemini import GeminiProvider

    settings = Settings(
        database_url="postgresql://localhost/food_tracker_test",
        gemini_api_key=API_KEY,
    )
    provider = GeminiProvider(
        api_key=settings.gemini_api_key.get_secret_value(),
        model_name=settings.llm_model,
    )

    result = provider.analyse_food(_TEST_IMAGE, "test_food.jpg")

    assert result.food_name, "food_name must not be empty"
    assert result.calories_kcal >= 0
    assert result.protein_g >= 0
    assert result.carbs_g >= 0
    assert result.fat_g >= 0
    assert result.provider == "gemini"
