"""LangGraph StateGraph compiled once at startup."""

from langgraph.graph import END, StateGraph

from sourcing_agent.graph.edges import (
    route_after_intake,
    route_after_rank,
    route_after_research,
)
from sourcing_agent.graph.nodes import (
    error_handler_node,
    intake_node,
    rank_node,
    research_node,
)
from sourcing_agent.graph.state import AgentState

_graph = None


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("intake", intake_node)
    builder.add_node("research", research_node)
    builder.add_node("rank", rank_node)
    builder.add_node("error_handler", error_handler_node)

    builder.set_entry_point("intake")

    builder.add_conditional_edges("intake", route_after_intake, {"research": "research", "error_handler": "error_handler"})
    builder.add_conditional_edges("research", route_after_research, {"rank": "rank", "error_handler": "error_handler"})
    builder.add_conditional_edges("rank", route_after_rank, {"__end__": END, "error_handler": "error_handler"})
    builder.add_edge("error_handler", END)

    return builder.compile()


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
