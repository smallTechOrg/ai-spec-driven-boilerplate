from food_tracker.domain import NutritionResult
from food_tracker.llm.providers.base import LLMProvider


class StubProvider(LLMProvider):
    """Returns deterministic hardcoded nutrition data — no API key required.

    Used in demo/offline mode and during Phase 2 testing.
    Stub output is clearly tagged so the UI can display a warning banner.
    """

    def analyse_food(self, image_bytes: bytes, image_filename: str) -> NutritionResult:
        return NutritionResult(
            food_name="[STUB] Grilled Chicken with Rice",
            calories_kcal=450.0,
            protein_g=38.0,
            carbs_g=42.0,
            fat_g=9.0,
            provider="stub",
        )
