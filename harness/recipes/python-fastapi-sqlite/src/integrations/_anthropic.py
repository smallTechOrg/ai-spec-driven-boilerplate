"""Real Anthropic provider — the single live LLM path.

Imported only when ``APPNAME_LLM_PROVIDER=anthropic``. Requires the optional
``llm`` extra (``uv sync --extra llm``), which installs the ``anthropic`` SDK.
The offline stub path never imports this module, so a fresh copy runs green
with no key and no extra.

Returns the same plan dict the rest of the agent expects:
  {"tool": "<name>", "parameters": {...}, "reasoning": "..."}      to act, or
  {"tool": "FINAL_ANSWER", "result": "<answer>"}                   to finish.

The plan shape is enforced with structured outputs so the agent loop always
receives valid JSON.
"""

import json
from typing import Any

from src.config import get_settings

# JSON schema for the agent's execution plan. structured outputs guarantee the
# response is one valid JSON object matching this shape.
_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tool": {
            "type": "string",
            "description": "A registered tool name, or 'FINAL_ANSWER' to finish.",
        },
        "parameters": {
            "type": "object",
            "description": "Arguments for the chosen tool (omit for FINAL_ANSWER).",
            "additionalProperties": True,
        },
        "reasoning": {"type": "string"},
        "result": {
            "type": "string",
            "description": "The final answer (only when tool == 'FINAL_ANSWER').",
        },
    },
    "required": ["tool"],
    "additionalProperties": False,
}


class AnthropicClient:
    """Async wrapper over the Anthropic Messages API."""

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        settings = get_settings()
        self._model = settings.llm_model or "claude-sonnet-4-6"
        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )

    async def complete(self, messages: list[dict]) -> dict[str, Any]:
        # The agent passes an OpenAI-style message list. Anthropic takes the
        # system prompt separately and only user/assistant roles in `messages`.
        system = "\n\n".join(
            m["content"] for m in messages if m.get("role") == "system"
        )
        convo = [
            {
                "role": "assistant" if m["role"] == "assistant" else "user",
                "content": m["content"],
            }
            for m in messages
            if m.get("role") in ("user", "assistant", "tool")
        ]

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=convo,
            output_config={
                "format": {"type": "json_schema", "schema": _PLAN_SCHEMA}
            },
        )

        text = next(
            (b.text for b in response.content if b.type == "text"), "{}"
        )
        return json.loads(text)
