from datetime import datetime, timezone

from food_tracker.db.models import FoodLog


def test_food_log_insert_and_read(db_session):
    log = FoodLog(
        image_filename="pizza.jpg",
        food_name="Margherita Pizza",
        calories_kcal=285,
        protein_g=11,
        carbs_g=36,
        fat_g=10,
        provider="stub",
    )
    db_session.add(log)
    db_session.flush()

    assert log.id is not None
    assert log.food_name == "Margherita Pizza"
    assert log.provider == "stub"


def test_food_log_analyzed_at_defaults_to_utc(db_session):
    log = FoodLog(
        image_filename="salad.jpg",
        food_name="Caesar Salad",
        calories_kcal=180,
        protein_g=14,
        carbs_g=8,
        fat_g=11,
        provider="stub",
    )
    db_session.add(log)
    db_session.flush()

    assert log.analyzed_at is not None
    assert isinstance(log.analyzed_at, datetime)
