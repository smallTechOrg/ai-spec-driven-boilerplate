from food_tracker.config.settings import Settings
from food_tracker.llm.providers.base import LLMProvider
from food_tracker.llm.providers.stub import StubProvider


def create_provider(settings: Settings) -> LLMProvider:
    if settings.gemini_api_key:
        from food_tracker.llm.providers.gemini import GeminiProvider

        return GeminiProvider(
            api_key=settings.gemini_api_key.get_secret_value(),
            model_name=settings.llm_model,
        )
    return StubProvider()
