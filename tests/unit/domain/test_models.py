import pytest
from pydantic import ValidationError

from food_tracker.domain import FoodLogCreate, NutritionResult


def test_nutrition_result_valid():
    result = NutritionResult(
        food_name="Banana",
        calories_kcal=89,
        protein_g=1.1,
        carbs_g=23,
        fat_g=0.3,
        provider="stub",
    )
    assert result.food_name == "Banana"
    assert result.calories_kcal == 89


def test_nutrition_result_rejects_negative_calories():
    with pytest.raises(ValidationError):
        NutritionResult(
            food_name="Invalid",
            calories_kcal=-10,
            protein_g=0,
            carbs_g=0,
            fat_g=0,
            provider="stub",
        )


def test_food_log_create_valid():
    log = FoodLogCreate(
        image_filename="burger.jpg",
        food_name="Cheeseburger",
        calories_kcal=550,
        protein_g=30,
        carbs_g=45,
        fat_g=25,
        provider="stub",
    )
    assert log.provider == "stub"
