from __future__ import annotations

from langgraph.graph import StateGraph, END

from lead_gen_agent.graph.nodes import extract_node, persist_node, score_node, search_node
from lead_gen_agent.graph.state import AgentState


def _route_after(node_name: str):
    def _router(state: AgentState) -> str:
        return "persist" if state.get("error") else node_name
    return _router


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("search", search_node)
    g.add_node("extract", extract_node)
    g.add_node("score", score_node)
    g.add_node("persist", persist_node)
    g.set_entry_point("search")
    g.add_conditional_edges("search", _route_after("extract"), {"extract": "extract", "persist": "persist"})
    g.add_conditional_edges("extract", _route_after("score"), {"score": "score", "persist": "persist"})
    g.add_edge("score", "persist")
    g.add_edge("persist", END)
    return g.compile()


agent_graph = _build_graph()
