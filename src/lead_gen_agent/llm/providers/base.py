from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    def complete(self, prompt: str) -> str: ...
