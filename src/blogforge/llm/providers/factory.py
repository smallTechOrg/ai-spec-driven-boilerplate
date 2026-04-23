from blogforge.config.settings import get_settings
from blogforge.llm.providers.base import LLMProvider
from blogforge.llm.providers.stub import StubProvider


def create_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_provider == "gemini":
        from blogforge.llm.providers.gemini import GeminiProvider
        return GeminiProvider(api_key=s.gemini_api_key, model=s.llm_model)
    return StubProvider()
