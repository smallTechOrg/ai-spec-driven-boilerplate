"""LangGraph ReAct loop — plan_action -> invoke_tool ↺ -> finalize / handle_error.

Storage-layer-agnostic: the graph never touches the DB. The example route persists
the result after ``graph.ainvoke`` returns.
"""

from langgraph.graph import END, StateGraph

from src.agent.nodes import finalize, handle_error, invoke_tool, plan_action
from src.agent.state import AgentState

MAX_ITERATIONS = 25


def _route(state: AgentState) -> str:
    if state.get("error"):
        return "handle_error"
    if state.get("result") is not None:
        return "finalize"
    if state.get("iterations", 0) >= MAX_ITERATIONS:
        return "handle_error"
    return "invoke_tool"


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("plan_action", plan_action)
    g.add_node("invoke_tool", invoke_tool)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("plan_action")

    g.add_conditional_edges(
        "plan_action",
        _route,
        {
            "invoke_tool": "invoke_tool",
            "finalize": "finalize",
            "handle_error": "handle_error",
        },
    )

    g.add_edge("invoke_tool", "plan_action")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)

    return g.compile()


graph = build_graph()
