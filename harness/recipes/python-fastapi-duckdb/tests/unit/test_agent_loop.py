"""The full stub ReAct loop via the echo tool — no keys, no domain content."""

from src.agent.graph import graph
from src.agent.state import AgentState


async def test_stub_loop_echoes_then_finishes():
    state: AgentState = {
        "run_id": 0,
        "user_input": "hello there",
        "tool_call_history": [],
        "result": None,
        "error": None,
        "iterations": 0,
    }
    final = await graph.ainvoke(state)

    assert final.get("error") is None
    # The stub finishes after one tool result with a generic [STUB] answer.
    assert final["result"].startswith("[STUB] Done.")

    # The echo tool ran on the user input — a "tool" message is present in history.
    tool_msgs = [m for m in final["tool_call_history"] if m["role"] == "tool"]
    assert tool_msgs, "expected the echo tool to have run"
    assert tool_msgs[0]["content"] == "echo: hello there"
