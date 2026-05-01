from langgraph.graph import StateGraph, END

from blogforge.graph.state import AgentState
from blogforge.graph.nodes import node_plan, node_draft, node_finalize, node_handle_error


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("plan", node_plan)
    graph.add_node("draft", node_draft)
    graph.add_node("finalize", node_finalize)
    graph.add_node("handle_error", node_handle_error)

    graph.set_entry_point("plan")
    graph.add_conditional_edges("plan", lambda s: "handle_error" if s.get("error") else "draft")
    graph.add_conditional_edges("draft", lambda s: "handle_error" if s.get("error") else "finalize")
    graph.add_conditional_edges("finalize", lambda s: "handle_error" if s.get("error") else END)
    graph.add_edge("handle_error", END)
    return graph.compile()


compiled_graph = build_graph()
