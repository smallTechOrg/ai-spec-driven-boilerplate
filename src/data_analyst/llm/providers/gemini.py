import google.generativeai as genai

from data_analyst.llm.providers.base import LLMProvider, LLMResponse, UsageStats


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def generate(self, prompt: str) -> LLMResponse:
        response = self._model.generate_content(prompt)
        usage = None
        if hasattr(response, "usage_metadata"):
            meta = response.usage_metadata
            usage = UsageStats(
                prompt_token_count=getattr(meta, "prompt_token_count", 0) or 0,
                candidates_token_count=getattr(meta, "candidates_token_count", 0) or 0,
            )
        return LLMResponse(text=response.text, usage=usage)
