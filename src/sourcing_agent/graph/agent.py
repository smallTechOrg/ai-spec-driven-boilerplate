from __future__ import annotations

from langgraph.graph import END, StateGraph

from sourcing_agent.graph.edges import after_enrich, after_research, after_score
from sourcing_agent.graph.nodes import enrich, finalize, handle_error, research, score
from sourcing_agent.graph.state import AgentState


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("research", research)
    g.add_node("enrich", enrich)
    g.add_node("score", score)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("research")
    g.add_conditional_edges(
        "research", after_research,
        {"enrich": "enrich", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "enrich", after_enrich,
        {"score": "score", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "score", after_score,
        {"finalize": "finalize", "handle_error": "handle_error"},
    )
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


agent_graph = _build_graph()
