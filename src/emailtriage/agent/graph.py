from langgraph.graph import StateGraph, END
from emailtriage.agent.state import TriageState
from emailtriage.agent.nodes import fetch_emails, classify_and_draft, persist_results, handle_error, finalize

def build_graph():
    g = StateGraph(TriageState)
    g.add_node("fetch_emails", fetch_emails)
    g.add_node("classify_and_draft", classify_and_draft)
    g.add_node("persist_results", persist_results)
    g.add_node("handle_error", handle_error)
    g.add_node("finalize", finalize)
    g.set_entry_point("fetch_emails")
    g.add_conditional_edges("fetch_emails",
        lambda s: "handle_error" if s.get("error") else "classify_and_draft",
        {"handle_error": "handle_error", "classify_and_draft": "classify_and_draft"})
    g.add_edge("classify_and_draft", "persist_results")
    g.add_edge("persist_results", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()

graph = build_graph()
