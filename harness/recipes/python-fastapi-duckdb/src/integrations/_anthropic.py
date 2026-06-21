"""Anthropic provider — the single real LLM path (optional ``llm`` extra).

Installed via ``uv sync --extra llm`` (the ``anthropic`` SDK). The default
provider is ``stub`` and needs no key; this path is exercised only when
APPNAME_LLM_PROVIDER=anthropic and APPNAME_ANTHROPIC_API_KEY is set.

It speaks the same contract as the stub: ``complete(messages) -> dict`` returning
either {"tool", "parameters", "reasoning"} or {"tool": "FINAL_ANSWER", "result"}.
The registered tools are exposed to the model as Claude tool definitions; a
FINAL_ANSWER is synthesized from the model's text when it stops calling tools.
"""

from typing import Any

from src.agent.tools import TOOL_REGISTRY
from src.config import get_settings

# Model id is fixed by the recipe; switch it in config if you change tiers.
_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 4096


def _tool_defs() -> list[dict]:
    """Expose the registered tools to Claude as tool definitions."""
    defs = []
    for tool in TOOL_REGISTRY.values():
        properties = {
            name: {"type": "string", "description": desc}
            for name, desc in tool.parameters.items()
        }
        defs.append(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties),
                },
            }
        )
    return defs


def _split_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Split our internal message list into (system_prompt, anthropic_messages)."""
    system = ""
    out: list[dict] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "system":
            system = content
        elif role in ("user", "assistant"):
            out.append({"role": role, "content": content})
        elif role == "tool":
            # Tool results are folded into the conversation as user turns.
            out.append({"role": "user", "content": f"Tool result:\n{content}"})
    return system, out


class AnthropicClient:
    async def complete(self, messages: list[dict]) -> dict[str, Any]:
        from anthropic import AsyncAnthropic  # imported lazily — optional `llm` extra

        settings = get_settings()
        client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())

        system, conv = _split_messages(messages)
        resp = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=system or "You are a helpful agent.",
            tools=_tool_defs(),
            messages=conv,
        )

        # If the model called a tool, surface the first tool call as a plan.
        for block in resp.content:
            if block.type == "tool_use":
                return {
                    "tool": block.name,
                    "parameters": dict(block.input),
                    "reasoning": "anthropic tool call",
                }

        # Otherwise the model produced a final textual answer.
        text = "".join(b.text for b in resp.content if b.type == "text")
        return {"tool": "FINAL_ANSWER", "result": text.strip()}
