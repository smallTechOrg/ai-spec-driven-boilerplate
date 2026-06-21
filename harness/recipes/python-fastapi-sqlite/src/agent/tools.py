from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Coroutine[Any, Any, Any]]


# The agent's tool registry. The executor replaces the example tool below with
# the project's real capabilities.
TOOL_REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    TOOL_REGISTRY[tool.name] = tool
    return tool


async def echo(text: str) -> str:
    """[REPLACE ME] Example tool — returns the input text prefixed with 'echo:'.
    Swap this for your real capability."""
    return f"echo: {text}"


# The ONLY registered tool. It exists to wire the whole vertical slice end to
# end (UI -> API -> graph -> tool -> stub LLM -> persistence -> response).
# Delete it and register your real tools instead.
register(
    Tool(
        name="echo",
        description=(
            "[REPLACE ME] Example tool — returns the input text prefixed with "
            "'echo:'. Swap this for your real capability."
        ),
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to echo back."}
            },
            "required": ["text"],
        },
        handler=echo,
    )
)
