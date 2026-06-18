from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    text: str
    usage: "UsageStats | None" = None


@dataclass
class UsageStats:
    prompt_token_count: int = 0
    candidates_token_count: int = 0


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> LLMResponse:
        ...
