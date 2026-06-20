from typing import TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: list[BaseMessage]    # PLAIN list — the nodes return the full merged list themselves (NO add_messages reducer)
    iterations: int
    answer: str | None
    run_id: str
