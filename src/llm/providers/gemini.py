from dataclasses import dataclass

from google import genai
from google.genai import types


@dataclass
class LLMResult:
    """A model response plus the real token usage from the provider.

    `text` is the generated content; `prompt_tokens`/`completion_tokens` come
    from `response.usage_metadata` so cost is measured, not estimated.
    """

    text: str
    prompt_tokens: int
    completion_tokens: int


class GeminiProvider:
    # Low cost tier for the Local Data Analyst — flash is fast and strong
    # enough for SQL drafting against a known schema and narration of aggregates.
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str, model: str, json_mode: bool = False) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL
        # When True, every call asks Gemini for `application/json` output so the
        # planner/narrator get clean, parseable JSON (no prose / fences). This is
        # provider-Gemini-specific and backward-safe; plain calls leave it off.
        self._json_mode = json_mode

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        """Backwards-compatible string call (text only)."""
        return self.call_model_usage(prompt, system=system).text

    def call_model_usage(
        self, prompt: str, *, system: str | None = None, json_mode: bool | None = None
    ) -> LLMResult:
        """Call the model and return text + real token usage metadata.

        `json_mode` (or the instance default set at construction) requests
        structured `application/json` output so JSON nodes get clean JSON.
        """
        want_json = self._json_mode if json_mode is None else json_mode
        config_kwargs: dict = {}
        if system:
            config_kwargs["system_instruction"] = system
        if want_json:
            config_kwargs["response_mime_type"] = "application/json"
        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        return LLMResult(
            text=response.text or "",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
