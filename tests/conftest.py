import pytest
import data_analysis_agent.config.settings as settings_module


@pytest.fixture(autouse=True)
def _reset_settings_singleton():
    """Reset cached settings so env patches take effect in every test."""
    settings_module._settings = None
    yield
    settings_module._settings = None
