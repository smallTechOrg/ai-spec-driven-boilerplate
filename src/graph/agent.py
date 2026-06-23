from langgraph.graph import StateGraph, END

from graph.state import AnalystState
from graph.nodes import (
    classify_intent,
    build_schema_context,
    call_llm_with_tools,
    execute_query,
    format_response,
    handle_error,
    finalize,
)
from graph.edges import (
    after_classify,
    after_schema,
    after_llm,
    after_execute,
    after_format,
)


def _build_graph() -> StateGraph:
    g = StateGraph(AnalystState)

    g.add_node("classify_intent", classify_intent)
    g.add_node("build_schema_context", build_schema_context)
    g.add_node("call_llm_with_tools", call_llm_with_tools)
    g.add_node("execute_query", execute_query)
    g.add_node("format_response", format_response)
    g.add_node("handle_error", handle_error)
    g.add_node("finalize", finalize)

    g.set_entry_point("classify_intent")

    g.add_conditional_edges(
        "classify_intent",
        after_classify,
        {
            "build_schema_context": "build_schema_context",
            "format_response": "format_response",
            "handle_error": "handle_error",
        },
    )
    g.add_conditional_edges(
        "build_schema_context",
        after_schema,
        {"call_llm_with_tools": "call_llm_with_tools", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "call_llm_with_tools",
        after_llm,
        {
            "execute_query": "execute_query",
            "format_response": "format_response",
            "handle_error": "handle_error",
        },
    )
    g.add_conditional_edges(
        "execute_query",
        after_execute,
        {"format_response": "format_response", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "format_response",
        after_format,
        {"finalize": "finalize", "handle_error": "handle_error"},
    )

    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)

    return g.compile()


analyst_graph = _build_graph()

# Keep backward compat with old runner.py import name
agentic_ai = analyst_graph
