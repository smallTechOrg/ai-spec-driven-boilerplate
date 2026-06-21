from typing import Any

from src.config import get_settings
from src.integrations.stubs.llm import StubLLMClient


class LLMClient:
    """Thin async LLM client. Swap the provider without changing call sites.

    Default provider is ``stub`` — no API key, fully offline. Set
    ``APPNAME_LLM_PROVIDER=anthropic`` (and ``APPNAME_ANTHROPIC_API_KEY``) to go
    live; that path needs the optional ``llm`` extra installed (``anthropic`` SDK).
    """

    async def complete(self, messages: list[dict]) -> dict[str, Any]:
        settings = get_settings()
        provider = settings.resolved_llm_provider

        if provider == "stub":
            return await StubLLMClient().complete(messages)

        if provider == "anthropic":
            # Imported lazily so the offline path never needs the `anthropic` SDK.
            from src.integrations._anthropic import AnthropicClient

            return await AnthropicClient().complete(messages)

        raise ValueError(
            f"Unknown LLM provider: {provider!r}. Use 'stub' or 'anthropic'."
        )


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
