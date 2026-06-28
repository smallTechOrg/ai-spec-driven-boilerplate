from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    load_profile,
    plan,
    generate_code,
    execute_code,
    inspect_result,
    answer,
    finalize,
    handle_error,
)
from graph.edges import route_after_inspect


def _build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("load_profile", load_profile)
    graph.add_node("plan", plan)
    graph.add_node("generate_code", generate_code)
    graph.add_node("execute_code", execute_code)
    graph.add_node("inspect_result", inspect_result)
    graph.add_node("answer", answer)
    graph.add_node("finalize", finalize)
    graph.add_node("handle_error", handle_error)
    # graph.add_node("clarify", clarify)   # Phase 4

    graph.set_entry_point("load_profile")

    graph.add_conditional_edges(
        "load_profile",
        lambda s: "handle_error" if s.get("error") else "plan",
    )
    graph.add_conditional_edges(
        "plan",
        lambda s: "handle_error" if s.get("error") else "generate_code",
    )
    graph.add_conditional_edges(
        "generate_code",
        lambda s: "handle_error" if s.get("error") else "execute_code",
    )
    graph.add_conditional_edges(
        "execute_code",
        lambda s: "handle_error" if s.get("error") else "inspect_result",
    )
    graph.add_conditional_edges(
        "inspect_result",
        route_after_inspect,
        {
            "answer": "answer",
            "generate_code": "generate_code",  # refine loop (guarded by MAX_ITERATIONS)
            # "clarify": "clarify",            # Phase 4
        },
    )

    graph.add_edge("answer", "finalize")
    graph.add_edge("finalize", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


agentic_ai = _build_graph()  # keep the exported name `agentic_ai`
