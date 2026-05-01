from abc import ABC, abstractmethod

from food_tracker.domain import NutritionResult


class LLMProvider(ABC):
    @abstractmethod
    def analyse_food(self, image_bytes: bytes, image_filename: str) -> NutritionResult:
        """Analyse a food photo and return nutrition data."""
