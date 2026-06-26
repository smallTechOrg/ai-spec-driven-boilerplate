from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import load_dataset, analyze_query, extract_table, handle_error, finalize
from graph.edges import after_load, after_analyze


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("load_dataset", load_dataset)
    g.add_node("analyze_query", analyze_query)
    g.add_node("extract_table", extract_table)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)
    g.set_entry_point("load_dataset")
    g.add_conditional_edges(
        "load_dataset",
        after_load,
        {"analyze_query": "analyze_query", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "analyze_query",
        after_analyze,
        {"extract_table": "extract_table", "handle_error": "handle_error"},
    )
    g.add_edge("extract_table", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


agentic_ai = _build_graph()
