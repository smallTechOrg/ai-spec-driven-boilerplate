"""Stub LLM — canned ReAct responses. No API key required (the default provider).

Deterministic by design: termination is driven by counting ``role == "tool"``
messages in history (>= 1), not a class-attribute counter, so concurrent runs and
re-entry behave correctly. Replace this + the echo tool with your real agent.
"""

from typing import Any


class StubLLMClient:
    async def complete(self, messages: list[dict]) -> dict[str, Any]:
        tool_results = [m for m in messages if m.get("role") == "tool"]

        # After one tool result is present, return a final answer.
        if len(tool_results) >= 1:
            return {
                "tool": "FINAL_ANSWER",
                "result": (
                    "[STUB] Done. I echoed your message — replace this stub + the echo "
                    "tool with your real agent."
                ),
            }

        # First call — drive the example echo tool with the user's input.
        user_input = next(
            (m["content"] for m in messages if m.get("role") == "user"),
            "",
        )
        return {
            "tool": "echo",
            "parameters": {"text": user_input},
            "reasoning": "[STUB] calling the example echo tool",
        }
