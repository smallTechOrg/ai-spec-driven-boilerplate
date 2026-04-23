from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from food_tracker.db.models import FoodLog
from food_tracker.graph.state import FoodState
from food_tracker.llm.providers.base import LLMProvider

log = structlog.get_logger()


def node_analyse_food(state: FoodState, provider: LLMProvider) -> FoodState:
    log.info("node_analyse_food.start", filename=state["image_filename"])
    try:
        result = provider.analyse_food(state["image_bytes"], state["image_filename"])
    except Exception as exc:
        log.error("node_analyse_food.failed", error=str(exc))
        return {**state, "error": f"Analysis failed: {exc}"}

    log.info(
        "node_analyse_food.done",
        food=result.food_name,
        calories=result.calories_kcal,
        provider=result.provider,
    )
    return {
        **state,
        "food_name": result.food_name,
        "calories_kcal": result.calories_kcal,
        "protein_g": result.protein_g,
        "carbs_g": result.carbs_g,
        "fat_g": result.fat_g,
        "provider": result.provider,
    }


def node_save_log(state: FoodState, session: Session) -> FoodState:
    log.info("node_save_log.start", food=state.get("food_name"))
    try:
        food_log = FoodLog(
            analyzed_at=datetime.now(timezone.utc),
            image_filename=state["image_filename"],
            food_name=state["food_name"],
            calories_kcal=state["calories_kcal"],
            protein_g=state["protein_g"],
            carbs_g=state["carbs_g"],
            fat_g=state["fat_g"],
            provider=state["provider"],
        )
        session.add(food_log)
        session.flush()
        run_id = food_log.id
    except Exception as exc:
        log.error("node_save_log.failed", error=str(exc))
        return {**state, "error": f"DB write failed: {exc}"}

    log.info("node_save_log.done", run_id=run_id)
    return {**state, "run_id": run_id}
