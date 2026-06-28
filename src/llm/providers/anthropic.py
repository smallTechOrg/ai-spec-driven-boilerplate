import anthropic as _sdk


class AnthropicProvider:
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str, model: str, json_mode: bool = False) -> None:
        self._client = _sdk.Anthropic(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL
        # Accepted for a uniform provider interface; Anthropic JSON adherence is
        # driven by the prompt + the parse-retry, so no special mime type here.
        self._json_mode = json_mode

    def call_model(
        self, prompt: str, *, system: str | None = None, json_mode: bool | None = None
    ) -> str:
        kwargs: dict = dict(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system
        msg = self._client.messages.create(**kwargs)
        return msg.content[0].text
