from data_analyst.llm.providers.base import LLMProvider, LLMResponse, UsageStats


class StubLLMProvider(LLMProvider):
    def generate(self, prompt: str) -> LLMResponse:
        prompt_upper = prompt.upper()
        if "<NODE:FORCE_FINALIZE>" in prompt_upper:
            text = (
                "FINAL ANSWER: Based on the analysis steps completed, here is a summary of findings. "
                "The data was partially analyzed before reaching the iteration limit."
            )
        elif "<NODE:PLAN>" in prompt_upper:
            text = "ACTION: describe()"
        else:
            text = "ACTION: head(5)"

        return LLMResponse(
            text=text,
            usage=UsageStats(prompt_token_count=10, candidates_token_count=20),
        )
