"""LangGraph graph assembly for the Data Analysis Agent."""

from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    load_dataset,
    plan_analysis,
    execute_code,
    reason_answer,
    handle_error,
    finalize,
)
from graph.edges import (
    after_load,
    after_plan,
    after_execute,
    after_reason,
)


def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("load_dataset", load_dataset)
    g.add_node("plan_analysis", plan_analysis)
    g.add_node("execute_code", execute_code)
    g.add_node("reason_answer", reason_answer)
    g.add_node("handle_error", handle_error)
    g.add_node("finalize", finalize)

    g.set_entry_point("load_dataset")

    g.add_conditional_edges(
        "load_dataset",
        after_load,
        {"plan_analysis": "plan_analysis", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "plan_analysis",
        after_plan,
        {"execute_code": "execute_code", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "execute_code",
        after_execute,
        {"reason_answer": "reason_answer", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "reason_answer",
        after_reason,
        {"finalize": "finalize", "handle_error": "handle_error"},
    )

    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)

    return g.compile()


agentic_ai = _build_graph()
