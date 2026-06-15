from data_analysis_agent.llm.providers.base import LLMProvider


class StubLLMProvider(LLMProvider):
    """Offline stub — returns plausible shaped output without any API call."""

    def complete(self, prompt: str) -> str:
        if "<node:analyze>" in prompt:
            return (
                "Based on the data provided, here is the analysis:\n\n"
                "The dataset contains structured tabular data across multiple columns. "
                "Looking at the values and distributions, the patterns suggest a typical "
                "business dataset with numerical and categorical features.\n\n"
                "**Note:** This is a stub response generated in offline mode. "
                "Set DATAANALYSIS_GEMINI_API_KEY to get real answers from Gemini."
            )
        return "(stub) No response — unrecognized node tag in prompt."
