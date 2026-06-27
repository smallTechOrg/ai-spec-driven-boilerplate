from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    load_profile,
    build_prompt,
    answer,
    finalize,
    handle_error,
)
from graph.edges import (
    after_load_profile,
    after_build_prompt,
    after_answer,
)


def _build_graph():
    g = StateGraph(AgentState)

    g.add_node("load_profile", load_profile)
    g.add_node("build_prompt", build_prompt)
    g.add_node("answer", answer)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("load_profile")

    g.add_conditional_edges(
        "load_profile",
        after_load_profile,
        {"handle_error": "handle_error", "build_prompt": "build_prompt"},
    )
    g.add_conditional_edges(
        "build_prompt",
        after_build_prompt,
        {"handle_error": "handle_error", "answer": "answer"},
    )
    g.add_conditional_edges(
        "answer",
        after_answer,
        {"handle_error": "handle_error", "finalize": "finalize"},
    )

    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)

    return g.compile()


agentic_ai = _build_graph()
