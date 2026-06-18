from data_analyst.llm.providers.base import LLMProvider


def create_llm_provider() -> LLMProvider:
    from data_analyst.config.settings import get_settings
    settings = get_settings()
    provider_name = settings.resolved_llm_provider

    if provider_name == "gemini":
        from data_analyst.llm.providers.gemini import GeminiLLMProvider
        return GeminiLLMProvider(
            api_key=settings.gemini_api_key.split("#")[0].strip(),
            model=settings.llm_model,
        )

    from data_analyst.llm.providers.stub import StubLLMProvider
    return StubLLMProvider()
