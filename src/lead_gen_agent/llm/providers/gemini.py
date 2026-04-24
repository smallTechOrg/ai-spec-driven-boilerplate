from __future__ import annotations

import os


class GeminiProvider:
    def __init__(self, model: str):
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def complete(self, prompt: str) -> str:
        resp = self._client.models.generate_content(model=self._model, contents=prompt)
        return resp.text or ""
