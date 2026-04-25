"""Factory — creates the correct LLMProvider based on resolved settings."""

from sourcing_agent.llm.providers.base import LLMProvider


def create_llm_provider() -> LLMProvider:
    from sourcing_agent.config.settings import get_settings

    settings = get_settings()
    provider_name = settings.resolved_llm_provider

    if provider_name == "gemini":
        from sourcing_agent.llm.providers.gemini import GeminiLLMProvider

        return GeminiLLMProvider(api_key=settings.gemini_api_key, model=settings.llm_model)

    from sourcing_agent.llm.providers.stub import StubLLMProvider

    return StubLLMProvider()
