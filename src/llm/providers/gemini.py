from google import genai
from google.genai import types

from llm.providers.base import LLMResponse


class GeminiProvider:
    DEFAULT_MODEL = "gemini-3.1-flash-lite"

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=system,
        ) if system else None
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        # Real usage from Gemini's usage_metadata (prompt_token_count =
        # input, candidates_token_count = output). Absent -> 0 (caller estimates).
        usage = getattr(response, "usage_metadata", None)
        tokens_input = int(getattr(usage, "prompt_token_count", 0) or 0)
        tokens_output = int(getattr(usage, "candidates_token_count", 0) or 0)
        return LLMResponse(response.text or "", tokens_input, tokens_output)

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        return self.complete(prompt, system=system).text
