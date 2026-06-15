from data_analysis_agent.llm.providers.base import LLMProvider


def create_llm_provider() -> LLMProvider:
    from data_analysis_agent.config.settings import get_settings
    settings = get_settings()

    if settings.resolved_llm_provider == "gemini":
        from data_analysis_agent.llm.providers.gemini import GeminiLLMProvider
        return GeminiLLMProvider(
            api_key=settings.gemini_api_key.split("#")[0].strip(),
            model=settings.llm_model,
        )

    from data_analysis_agent.llm.providers.stub import StubLLMProvider
    return StubLLMProvider()
