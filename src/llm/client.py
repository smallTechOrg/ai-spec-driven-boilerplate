from config.settings import get_settings


def _make_provider(json_mode: bool = False):
    s = get_settings()
    provider = s.llm_provider

    # auto-detect from whichever key is set
    if not provider:
        if s.anthropic_api_key:
            provider = "anthropic"
        elif s.gemini_api_key:
            provider = "gemini"
        else:
            raise RuntimeError(
                "No LLM provider configured. Set AGENT_ANTHROPIC_API_KEY or "
                "AGENT_GEMINI_API_KEY in .env, or set AGENT_LLM_PROVIDER explicitly."
            )

    if provider == "anthropic":
        from llm.providers.anthropic import AnthropicProvider
        return AnthropicProvider(
            api_key=s.anthropic_api_key, model=s.llm_model, json_mode=json_mode
        )
    if provider == "gemini":
        from llm.providers.gemini import GeminiProvider
        return GeminiProvider(
            api_key=s.gemini_api_key, model=s.llm_model, json_mode=json_mode
        )

    raise RuntimeError(f"Unknown LLM provider: {provider!r}. Supported: anthropic, gemini")


class LLMClient:
    def __init__(self, json_mode: bool = False) -> None:
        # `json_mode` is set at construction so the call signature stays
        # `call_model_usage(prompt, *, system=...)` — the exact surface the
        # privacy spy patches. Structured-output is applied inside the provider.
        self._provider = _make_provider(json_mode=json_mode)

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        return self._provider.call_model(prompt, system=system)

    def call_model_usage(self, prompt: str, *, system: str | None = None):
        """Call the model and return an LLMResult (text + real token usage).

        Used by the graph nodes so per-run token/cost counts are real, not
        estimated. Falls back to a zero-usage result if a provider has not
        implemented usage metadata.
        """
        if hasattr(self._provider, "call_model_usage"):
            return self._provider.call_model_usage(prompt, system=system)
        from llm.providers.gemini import LLMResult

        text = self._provider.call_model(prompt, system=system)
        return LLMResult(text=text, prompt_tokens=0, completion_tokens=0)
