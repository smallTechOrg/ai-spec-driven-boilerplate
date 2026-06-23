from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    generate_sql,
    execute_sql,
    compose_answer,
    finalize,
    handle_error,
)
from graph.edges import (
    after_generate_sql,
    after_execute_sql,
    after_compose_answer,
)


def _build_graph():
    g = StateGraph(AgentState)

    g.add_node("generate_sql", generate_sql)
    g.add_node("execute_sql", execute_sql)
    g.add_node("compose_answer", compose_answer)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("generate_sql")

    g.add_conditional_edges(
        "generate_sql",
        after_generate_sql,
        {"execute_sql": "execute_sql", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "execute_sql",
        after_execute_sql,
        {"compose_answer": "compose_answer", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "compose_answer",
        after_compose_answer,
        {"finalize": "finalize", "handle_error": "handle_error"},
    )

    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)

    return g.compile()


agentic_ai = _build_graph()
