"""Single Gemini accessor via LangChain init_chat_model (patterns/llm-providers.md).

Never import the Gemini SDK directly in nodes and never build a bespoke LLMClient — every
model call goes through here so provider/model/routing live in one place. Real-first: the
key is required (configure_provider_env fails loud if missing).
"""

from __future__ import annotations

from functools import lru_cache

from langchain.chat_models import init_chat_model

from datachat.config.settings import get_settings


@lru_cache(maxsize=4)
def _build(model: str, provider: str):
    return init_chat_model(model, model_provider=provider, temperature=0)


def get_model(*, hard: bool = False):
    """Return the chat model. `hard=True` routes to the stronger model for hard reasoning."""
    settings = get_settings()
    settings.configure_provider_env()
    model = "gemini-2.5-pro" if hard else settings.llm_model
    return _build(model, settings.llm_provider)


def usage_from_response(response) -> tuple[int, int]:
    """Extract (input_tokens, output_tokens) from an AIMessage, tolerating shapes."""
    meta = getattr(response, "usage_metadata", None) or {}
    return int(meta.get("input_tokens", 0)), int(meta.get("output_tokens", 0))
