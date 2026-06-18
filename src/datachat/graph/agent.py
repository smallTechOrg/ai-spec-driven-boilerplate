"""StateGraph assembly — compiled once at import (no checkpointer in v1)."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from datachat.graph.edges import route_after_context, route_after_plan
from datachat.graph.nodes import (
    node_assemble_context,
    node_execute_action,
    node_finalize,
    node_force_finalize,
    node_handle_error,
    node_plan_action,
)
from datachat.graph.state import AgentState


@lru_cache(maxsize=1)
def get_compiled_graph():
    graph = StateGraph(AgentState)

    graph.add_node("assemble_context", node_assemble_context)
    graph.add_node("plan_action", node_plan_action)
    graph.add_node("execute_action", node_execute_action)
    graph.add_node("finalize", node_finalize)
    graph.add_node("force_finalize", node_force_finalize)
    graph.add_node("handle_error", node_handle_error)

    graph.set_entry_point("assemble_context")
    graph.add_conditional_edges("assemble_context", route_after_context)
    graph.add_conditional_edges("plan_action", route_after_plan)
    graph.add_edge("execute_action", "plan_action")
    graph.add_edge("finalize", END)
    graph.add_edge("force_finalize", END)
    graph.add_edge("handle_error", END)

    return graph.compile()
