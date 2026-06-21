"""Tools — a typed registry the ReAct loop dispatches to.

Tools fail SOFT: a handler returns a string and never raises, so the model can
recover. The example ``echo`` tool is the ONLY registered tool — swap it for your
real capability.
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Coroutine[Any, Any, Any]]
    category: str = "internal"  # data | service | compute | internal


# Register tools here. The executor swaps the example for project-specific tools.
TOOL_REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    TOOL_REGISTRY[tool.name] = tool
    return tool


async def echo(text: str) -> str:
    """[REPLACE ME] Example tool — returns the input text prefixed with 'echo:'.
    Swap this for your real capability."""
    return f"echo: {text}"


register(
    Tool(
        name="echo",
        description=(
            "[REPLACE ME] Example tool — returns the input text prefixed with 'echo:'. "
            "Swap this for your real capability."
        ),
        parameters={"text": "string — the text to echo back"},
        handler=echo,
        category="internal",
    )
)
