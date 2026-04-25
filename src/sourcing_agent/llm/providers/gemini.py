"""Google Gemini LLM provider."""

from sourcing_agent.llm.providers.base import LLMProvider


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return response.text or ""
