from __future__ import annotations


class GeminiProvider:
    def __init__(self, model: str, api_key: str):
        from google import genai
        self._client = genai.Client(api_key=api_key.strip())
        self._model = model

    def complete(self, prompt: str) -> str:
        wants_json = "<node:extract>" in prompt or "<node:score>" in prompt
        config = {"response_mime_type": "application/json"} if wants_json else None
        resp = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return resp.text or ""
