import anthropic as _sdk

from llm.providers.gemini import LLMResult


class AnthropicProvider:
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str, model: str) -> None:
        self._client = _sdk.Anthropic(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        return self.call_with_usage(prompt, system=system).text

    def call_with_usage(self, prompt: str, *, system: str | None = None) -> LLMResult:
        kwargs: dict = dict(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system
        msg = self._client.messages.create(**kwargs)
        usage = getattr(msg, "usage", None)
        prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return LLMResult(
            text=msg.content[0].text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
