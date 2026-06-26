"""Provider contract.

Every LLM provider (gemini / openrouter / stub / anthropic) implements this
single uniform interface. `LLMClient` is the only caller; no graph node ever
touches a provider SDK directly.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Uniform completion interface shared by all providers.

    A provider takes a fully-assembled prompt and an optional system
    instruction and returns the model's text reply. Implementations read their
    own `api_key` / `model` in their constructor; the stub takes neither.
    """

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        """Return the model's text reply for `prompt` (with optional `system`)."""
        ...
