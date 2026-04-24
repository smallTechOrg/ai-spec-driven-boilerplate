from __future__ import annotations

from lead_gen_agent.config.settings import get_settings
from lead_gen_agent.llm.providers.base import LLMProvider


def get_llm_client() -> LLMProvider:
    settings = get_settings()
    provider = settings.resolved_llm_provider
    if provider == "gemini":
        from lead_gen_agent.llm.providers.gemini import GeminiProvider
        return GeminiProvider(model=settings.llm_model, api_key=settings.gemini_api_key)
    from lead_gen_agent.llm.providers.stub import StubProvider
    return StubProvider()
