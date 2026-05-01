from __future__ import annotations


class GeminiLLMProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai  # type: ignore

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def complete(self, prompt: str) -> str:
        client = self._get_client()
        resp = client.models.generate_content(model=self._model, contents=prompt)
        return resp.text or ""
