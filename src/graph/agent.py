from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    profile,
    plan,
    local_execute,
    aggregate,
    narrate,
    suggest_follow_ups,
    finalize,
    handle_error,
)
from graph.edges import route_on_error


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("profile", profile)
    g.add_node("plan", plan)
    g.add_node("local_execute", local_execute)
    g.add_node("aggregate", aggregate)
    g.add_node("narrate", narrate)
    g.add_node("suggest_follow_ups", suggest_follow_ups)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("profile")

    g.add_conditional_edges(
        "profile",
        lambda s: route_on_error(s, "plan"),
        {"plan": "plan", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "plan",
        lambda s: route_on_error(s, "local_execute"),
        {"local_execute": "local_execute", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "local_execute",
        lambda s: route_on_error(s, "aggregate"),
        {"aggregate": "aggregate", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "aggregate",
        lambda s: route_on_error(s, "narrate"),
        {"narrate": "narrate", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "narrate",
        lambda s: route_on_error(s, "suggest_follow_ups"),
        {"suggest_follow_ups": "suggest_follow_ups", "handle_error": "handle_error"},
    )

    g.add_edge("suggest_follow_ups", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


agentic_ai = _build_graph()
