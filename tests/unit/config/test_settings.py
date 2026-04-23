import pytest
from pydantic import ValidationError

from food_tracker.config.settings import Settings


def test_settings_requires_postgres_url():
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///test.db")


def test_settings_provider_stub_when_no_key():
    s = Settings(database_url="postgresql://localhost/food_tracker_test")
    assert s.provider == "stub"


def test_settings_provider_gemini_when_key_present():
    s = Settings(
        database_url="postgresql://localhost/food_tracker_test",
        gemini_api_key="fake-key",
    )
    assert s.provider == "gemini"
