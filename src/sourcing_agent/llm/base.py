from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    name: str

    def complete(self, prompt: str) -> str:
        ...
