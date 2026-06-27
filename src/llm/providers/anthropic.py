import anthropic as _sdk

from llm.providers.base import LLMResponse


class AnthropicProvider:
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str, model: str) -> None:
        self._client = _sdk.Anthropic(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        kwargs: dict = dict(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system
        msg = self._client.messages.create(**kwargs)
        usage = getattr(msg, "usage", None)
        tokens_input = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_output = int(getattr(usage, "output_tokens", 0) or 0)
        return LLMResponse(msg.content[0].text, tokens_input, tokens_output)

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        return self.complete(prompt, system=system).text
