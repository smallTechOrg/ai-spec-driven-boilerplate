from blogforge.llm.providers.base import LLMProvider
from blogforge.llm.providers.factory import create_llm_provider

_client: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _client
    if _client is None:
        _client = create_llm_provider()
    return _client


def set_llm(provider: LLMProvider) -> None:
    """Test hook — override the active provider."""
    global _client
    _client = provider
