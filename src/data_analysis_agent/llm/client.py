from data_analysis_agent.llm.providers.base import LLMProvider


class LLMClient:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def complete(self, prompt: str) -> str:
        return self._provider.complete(prompt)


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        from data_analysis_agent.llm.providers.factory import create_llm_provider
        _client = LLMClient(create_llm_provider())
    return _client
