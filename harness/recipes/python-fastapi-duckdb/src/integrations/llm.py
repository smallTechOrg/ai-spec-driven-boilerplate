"""Thin async LLM client — swap the provider without changing call sites.

Default provider is ``stub`` (no key, runs offline). ``anthropic`` is the single
real provider, gated behind the optional ``llm`` extra. There are no dead provider
branches pointing at modules that don't exist.
"""

from typing import Any

from src.config import get_settings
from src.integrations.stubs.llm import StubLLMClient


class LLMClient:
    async def complete(self, messages: list[dict]) -> dict[str, Any]:
        provider = get_settings().resolved_llm_provider

        if provider == "stub":
            return await StubLLMClient().complete(messages)

        if provider == "anthropic":
            from src.integrations._anthropic import AnthropicClient

            return await AnthropicClient().complete(messages)

        raise ValueError(
            f"Unknown LLM provider: {provider!r} (expected 'stub' or 'anthropic')"
        )


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
