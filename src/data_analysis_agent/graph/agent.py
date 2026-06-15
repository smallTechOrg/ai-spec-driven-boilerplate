from langgraph.graph import StateGraph, END

from data_analysis_agent.graph.state import AgentState
from data_analysis_agent.graph.nodes import load_data, analyze, finalize, handle_error
from data_analysis_agent.graph.edges import after_load_data, after_analyze, after_finalize


def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("load_data", load_data)
    g.add_node("analyze", analyze)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("load_data")

    g.add_conditional_edges(
        "load_data", after_load_data,
        {"analyze": "analyze", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "analyze", after_analyze,
        {"finalize": "finalize", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "finalize", after_finalize,
        {"end": END, "handle_error": "handle_error"},
    )
    g.add_edge("handle_error", END)

    return g.compile()


agent_graph = _build_graph()
