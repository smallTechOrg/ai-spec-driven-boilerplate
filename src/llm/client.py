from config.settings import get_settings
from llm.providers.base import LLMResponse


def _resolve_provider_name() -> str:
    """Resolve the provider name to use (the auto-detect / explicit rule).

    Explicit `AGENT_LLM_PROVIDER` wins (including `stub`). When blank, auto-detect
    from whichever key is set, in order: anthropic -> gemini -> openrouter. With
    no key set, fall back to the offline `stub` (never raises).
    """
    s = get_settings()
    provider = s.llm_provider

    if provider:
        return provider

    if s.anthropic_api_key:
        return "anthropic"
    if s.gemini_api_key:
        return "gemini"
    if s.openrouter_api_key:
        return "openrouter"
    return "stub"


def _make_provider():
    s = get_settings()
    provider = _resolve_provider_name()

    if provider == "anthropic":
        from llm.providers.anthropic import AnthropicProvider
        return provider, AnthropicProvider(api_key=s.anthropic_api_key, model=s.llm_model)
    if provider == "gemini":
        from llm.providers.gemini import GeminiProvider
        return provider, GeminiProvider(api_key=s.gemini_api_key, model=s.llm_model)
    if provider == "openrouter":
        from llm.providers.openrouter import OpenRouterProvider
        return provider, OpenRouterProvider(api_key=s.openrouter_api_key, model=s.llm_model)
    if provider == "stub":
        from llm.providers.stub import StubProvider
        return provider, StubProvider(api_key=s.gemini_api_key, model=s.llm_model)

    raise RuntimeError(
        f"Unknown LLM provider: {provider!r}. "
        "Supported: anthropic, gemini, openrouter, stub."
    )


class LLMClient:
    def __init__(self) -> None:
        self._provider_name, self._provider = _make_provider()

    @property
    def provider(self) -> str:
        """The resolved provider name (e.g. 'gemini', 'stub', 'openrouter').

        Read by `/health` and the UI to drive the offline stub-mode banner.
        """
        return self._provider_name

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        """Return the model's reply + REAL token usage (provider-reported)."""
        return self._provider.complete(prompt, system=system)

    def call_model(self, prompt: str, *, system: str | None = None) -> str:
        return self._provider.call_model(prompt, system=system)
