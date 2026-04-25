"""LLM client — thin wrapper that holds a provider instance."""

from sourcing_agent.llm.providers.base import LLMProvider
from sourcing_agent.llm.providers.factory import create_llm_provider

_client: "LLMClient | None" = None


class LLMClient:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate(self, prompt: str) -> str:
        return self._provider.generate(prompt)

    @property
    def provider_name(self) -> str:
        return type(self._provider).__name__


def get_llm_client() -> "LLMClient":
    global _client
    if _client is None:
        _client = LLMClient(create_llm_provider())
    return _client


def reset_llm_client() -> None:
    """Reset cached client — used in tests only."""
    global _client
    _client = None
