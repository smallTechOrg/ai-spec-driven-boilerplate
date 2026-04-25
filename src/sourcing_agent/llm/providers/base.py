"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send prompt and return the text response."""
