from datetime import datetime

from pydantic import BaseModel, Field


class NutritionResult(BaseModel):
    food_name: str
    calories_kcal: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    provider: str


class FoodLogCreate(BaseModel):
    image_filename: str
    food_name: str
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    provider: str


class FoodLogRead(BaseModel):
    id: int
    analyzed_at: datetime
    image_filename: str
    food_name: str
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    provider: str

    model_config = {"from_attributes": True}
