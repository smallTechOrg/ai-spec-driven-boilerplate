"""Exercise the full stub ReAct loop via the example echo tool — fully offline."""

from src.agent.graph import graph
from src.agent.state import AgentState
from src.agent.tools import TOOL_REGISTRY, echo


async def test_echo_is_the_only_registered_tool():
    assert list(TOOL_REGISTRY) == ["echo"]


async def test_echo_tool_returns_prefixed_text():
    assert await echo("hi") == "echo: hi"


async def test_stub_loop_runs_end_to_end():
    state: AgentState = {
        "run_id": 0,
        "user_input": "hello world",
        "tool_call_history": [],
        "result": None,
        "error": None,
        "iterations": 0,
    }
    final = await graph.ainvoke(state)

    assert final.get("error") is None
    assert final["result"].startswith("[STUB] Done.")

    # The echo tool ran: its result is in history exactly once.
    tool_msgs = [m for m in final["tool_call_history"] if m["role"] == "tool"]
    assert tool_msgs == [{"role": "tool", "content": "echo: hello world"}]

    # Deterministic termination: one tool call, then FINAL_ANSWER.
    assert final["iterations"] == 2
