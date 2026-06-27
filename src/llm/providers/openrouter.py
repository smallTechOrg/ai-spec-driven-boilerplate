"""OpenRouter provider.

Alternate LLM provider implementing the uniform `call_model` contract via the
OpenAI-compatible chat-completions HTTP endpoint. Selected when
`AGENT_OPENROUTER_API_KEY` is the only key set, or `AGENT_LLM_PROVIDER=openrouter`
is explicit. Not exercised by the offline gate (no key); kept simple and
correct-by-inspection.
"""
from __future__ import annotations

import httpx

from llm.providers.base import LLMResponse

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT = 60.0


class OpenRouterProvider:
    # A widely-available default model on OpenRouter; overridable via AGENT_LLM_MODEL.
    DEFAULT_MODEL = "google/gemini-2.5-flash"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self._model, "messages": messages}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        response = httpx.post(
            _ENDPOINT, json=payload, headers=headers, timeout=_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        # OpenAI-compatible usage block (prompt_tokens / completion_tokens).
        usage = data.get("usage") or {}
        tokens_input = int(usage.get("prompt_tokens", 0) or 0)
        tokens_output = int(usage.get("completion_tokens", 0) or 0)
        return LLMResponse(text, tokens_input, tokens_output)

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        return self.complete(prompt, system=system).text
