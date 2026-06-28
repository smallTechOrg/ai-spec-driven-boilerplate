from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    plan,
    generate_code,
    execute,
    verify,
    finalize,
    handle_error,
)
from graph.edges import route_after_verify, increment_step


def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)
    g.add_node("plan", plan)
    g.add_node("generate_code", generate_code)
    g.add_node("execute", execute)
    g.add_node("verify", verify)
    g.add_node("increment", increment_step)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("plan")
    g.add_edge("plan", "generate_code")
    g.add_edge("generate_code", "execute")
    g.add_edge("execute", "verify")
    g.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "finalize": "finalize",
            "plan": "increment",      # retry path bumps the step counter first
            "handle_error": "handle_error",
        },
    )
    g.add_edge("increment", "plan")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


agentic_ai = _build_graph()
