class StubProvider:
    """Deterministic offline provider — used for tests and when no API key is configured."""

    def generate(self, prompt: str) -> str:
        p = prompt.lower()
        if "outline" in p:
            return "- Intro\n- Main point\n- Conclusion"
        if "title" in p:
            return "A Stub Title"
        return (
            "# Stub article\n\n"
            "This is a deterministic placeholder produced without calling an LLM. "
            "Configure BLOGFORGE_LLM_PROVIDER=gemini and set BLOGFORGE_GEMINI_API_KEY to get real output."
        )
