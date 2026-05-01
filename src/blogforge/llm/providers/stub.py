STUB_MARKER = "[stub]"


class StubProvider:
    """Deterministic offline provider. Distinct output per pipeline node so the
    resulting article is recognisably article-shaped (title, paragraphs) even
    without a real LLM. Uses node-specific markers the nodes inject into prompts
    (not fragile keyword matching on prose).
    """

    def generate(self, prompt: str) -> str:
        if "<node:plan>" in prompt:
            return (
                "- Why the topic matters\n"
                "- The core idea in one sentence\n"
                "- Two concrete examples\n"
                "- What to try next"
            )
        if "<node:title>" in prompt:
            topic = _extract(prompt, "topic:")
            return f"Notes on {topic}" if topic else f"{STUB_MARKER} A working title"
        if "<node:draft>" in prompt:
            topic = _extract(prompt, "topic:") or "the topic"
            return (
                f"{STUB_MARKER}\n\n"
                f"This is a placeholder article about **{topic}** generated without calling an LLM.\n\n"
                "## Why it matters\n\nReplace `BLOGFORGE_LLM_PROVIDER=stub` with `gemini` and set "
                "`BLOGFORGE_GEMINI_API_KEY` in `.env` to get real content here.\n\n"
                "## The core idea\n\nThe pipeline ran end-to-end: plan → draft → finalize, and "
                "persisted this article to Postgres. That is what this stub exists to prove.\n\n"
                "## What to try next\n\nCreate another writer with a different persona and regenerate."
            )
        return f"{STUB_MARKER} (unrecognised prompt)"


def _extract(prompt: str, key: str) -> str:
    for line in prompt.splitlines():
        low = line.lower()
        if low.startswith(key):
            return line.split(":", 1)[1].strip()
    return ""
