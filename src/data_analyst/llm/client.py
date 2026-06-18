from data_analyst.llm.providers.base import LLMProvider, LLMResponse

_provider: LLMProvider | None = None


def get_llm_client() -> LLMProvider:
    global _provider
    if _provider is None:
        from data_analyst.llm.providers.factory import create_llm_provider
        _provider = create_llm_provider()
    return _provider


def reset_llm_client() -> None:
    global _provider
    _provider = None
