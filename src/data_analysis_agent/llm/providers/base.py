from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Send prompt and return text response."""
