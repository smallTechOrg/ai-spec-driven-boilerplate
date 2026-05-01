from __future__ import annotations

from sourcing_agent.config.settings import get_settings
from sourcing_agent.llm.base import LLMProvider
from sourcing_agent.llm.gemini import GeminiLLMProvider
from sourcing_agent.llm.stub import StubLLMProvider


def create_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.resolved_llm_provider == "gemini":
        return GeminiLLMProvider(api_key=s.gemini_api_key, model=s.llm_model)
    return StubLLMProvider()
