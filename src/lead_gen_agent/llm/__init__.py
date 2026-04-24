"""Factory — create the correct LLM provider based on resolved settings."""
from __future__ import annotations

from lead_gen_agent.config import get_settings
from lead_gen_agent.llm.providers.base import LLMProvider
from lead_gen_agent.llm.providers.gemini import GeminiProvider
from lead_gen_agent.llm.providers.stub import StubLLMProvider


def create_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.resolved_llm_provider
    if provider == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.llm_model,
        )
    return StubLLMProvider()
