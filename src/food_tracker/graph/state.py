from typing import TypedDict


class FoodState(TypedDict):
    # Input
    image_bytes: bytes
    image_filename: str

    # Analysis output (populated by node_analyse_food)
    food_name: str | None
    calories_kcal: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    provider: str | None

    # DB output (populated by node_save_log)
    run_id: int | None

    # Control
    error: str | None
