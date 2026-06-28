from dataclasses import dataclass

from google import genai
from google.genai import types


@dataclass
class LLMResult:
    """LLM response text plus token usage from the provider."""

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GeminiProvider:
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        return self.call_with_usage(prompt, system=system).text

    def call_with_usage(self, prompt: str, *, system: str | None = None) -> LLMResult:
        config = (
            types.GenerateContentConfig(system_instruction=system) if system else None
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        total_tokens = int(getattr(usage, "total_token_count", 0) or 0)
        if not total_tokens:
            total_tokens = prompt_tokens + completion_tokens
        return LLMResult(
            text=response.text or "",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
