from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import profile_data, needs_clarification, inspect_quality, plan_and_code, execute_code, reflect_and_retry, format_response, handle_error
from graph.edges import after_clarification, after_plan, after_execute, after_execute_p3


def _build_profile_graph():
    g = StateGraph(AgentState)
    g.add_node("profile_data", profile_data)
    g.set_entry_point("profile_data")
    g.add_edge("profile_data", END)
    return g.compile()


def _build_qa_graph():
    g = StateGraph(AgentState)
    g.add_node("needs_clarification", needs_clarification)
    g.add_node("inspect_quality", inspect_quality)
    g.add_node("plan_and_code", plan_and_code)
    g.add_node("execute_code", execute_code)
    g.add_node("reflect_and_retry", reflect_and_retry)
    g.add_node("format_response", format_response)
    g.add_node("handle_error", handle_error)
    g.set_entry_point("needs_clarification")
    g.add_conditional_edges(
        "needs_clarification",
        after_clarification,
        {"inspect_quality": "inspect_quality", END: END},
    )
    g.add_edge("inspect_quality", "plan_and_code")
    g.add_conditional_edges(
        "plan_and_code",
        after_plan,
        {"execute_code": "execute_code", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "execute_code",
        after_execute_p3,
        {"format_response": "format_response", "reflect_and_retry": "reflect_and_retry", "handle_error": "handle_error"},
    )
    g.add_edge("reflect_and_retry", "execute_code")
    g.add_edge("format_response", END)
    g.add_edge("handle_error", END)
    return g.compile()


profile_graph = _build_profile_graph()
qa_graph = _build_qa_graph()
