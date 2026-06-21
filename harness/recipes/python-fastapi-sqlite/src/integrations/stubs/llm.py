"""Stub LLM — returns canned ReAct responses. No API key, fully offline.

The default provider. It drives the example `echo` tool end to end so the whole
slice (UI -> API -> graph -> tool -> persistence -> response) is exercisable with
zero keys. Termination is driven by counting tool results already in history, so
the loop is deterministic and stateless. Replace this stub and the example tool
with your real agent.
"""

from typing import Any


class StubLLMClient:
    async def complete(self, messages: list[dict]) -> dict[str, Any]:
        # Drive termination off history, not an instance counter, so the loop is
        # deterministic regardless of how the client is constructed.
        tool_results = [m for m in messages if m.get("role") == "tool"]
        if tool_results:
            return {
                "tool": "FINAL_ANSWER",
                "result": (
                    "[STUB] Done. I echoed your message — replace this stub + "
                    "the echo tool with your real agent."
                ),
            }

        # First call — invoke the example echo tool with the user's input.
        user_input = next(
            (m["content"] for m in messages if m.get("role") == "user"),
            "",
        )
        return {
            "tool": "echo",
            "parameters": {"text": user_input},
            "reasoning": "[STUB] calling the example echo tool",
        }
