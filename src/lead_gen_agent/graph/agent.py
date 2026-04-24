"""Compiled LangGraph StateGraph — created once at import time."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from lead_gen_agent.graph.edges import route_on_error
from lead_gen_agent.graph.nodes import (
    enrich_node,
    handle_error,
    save_node,
    search_node,
)
from lead_gen_agent.graph.state import AgentState


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("search_node", search_node)
    g.add_node("enrich_node", enrich_node)
    g.add_node("save_node", save_node)
    g.add_node("handle_error", handle_error)

    g.add_edge(START, "search_node")

    g.add_conditional_edges(
        "search_node",
        route_on_error,
        {"continue": "enrich_node", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "enrich_node",
        route_on_error,
        {"continue": "save_node", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "save_node",
        route_on_error,
        {"continue": END, "handle_error": "handle_error"},
    )

    g.add_edge("handle_error", END)

    return g


# Compiled once — safe to import from anywhere
compiled_graph = build_graph().compile()
