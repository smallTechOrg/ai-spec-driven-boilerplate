"""Assembles the data-analysis LangGraph (exported as ``agentic_ai``).

load_context -> plan -> generate_code -> execute_local -> visualize -> finalize
with conditional error edges to handle_error and a single self-correction loop
(execute_local -> generate_code).
"""

from functools import partial

from langgraph.graph import END, StateGraph

from graph.edges import route_after_execute, route_on_error
from graph.nodes import (
    execute_local,
    finalize,
    generate_code,
    handle_error,
    load_context,
    plan,
    visualize,
)
from graph.state import AgentState

# Linear successor for each error-guarded node.
_NEXT = {
    "load_context": "plan",
    "plan": "generate_code",
    "generate_code": "execute_local",
    "visualize": "finalize",
}


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("load_context", load_context)
    g.add_node("plan", plan)
    g.add_node("generate_code", generate_code)
    g.add_node("execute_local", execute_local)
    g.add_node("visualize", visualize)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("load_context")

    for node, nxt in _NEXT.items():
        g.add_conditional_edges(
            node,
            partial(route_on_error, next_node=nxt),
            {"handle_error": "handle_error", nxt: nxt},
        )

    g.add_conditional_edges(
        "execute_local",
        route_after_execute,
        {
            "generate_code": "generate_code",
            "visualize": "visualize",
            "handle_error": "handle_error",
        },
    )

    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


agentic_ai = _build_graph()
