from sqlalchemy.orm import Session

from food_tracker.graph.nodes import node_analyse_food, node_save_log
from food_tracker.graph.state import FoodState
from food_tracker.llm.providers.base import LLMProvider


def run_pipeline(
    image_bytes: bytes,
    image_filename: str,
    provider: LLMProvider,
    session: Session,
) -> FoodState:
    state: FoodState = {
        "image_bytes": image_bytes,
        "image_filename": image_filename,
        "food_name": None,
        "calories_kcal": None,
        "protein_g": None,
        "carbs_g": None,
        "fat_g": None,
        "provider": None,
        "run_id": None,
        "error": None,
    }

    state = node_analyse_food(state, provider)
    if state["error"]:
        return state

    state = node_save_log(state, session)
    return state
