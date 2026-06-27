from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    guard_input, load_dataset, propose_code, execute_code, explain_result,
    handle_error, finalize,
    load_memory, react, guard_output, write_memory,
)
from graph.edges import after_execute, after_react


def _build_graph() -> StateGraph:
    """The Data-Analysis graph: LLM-plan -> local-execute -> LLM-explain with a
    bounded code-repair loop. (The legacy transform_text / react seam nodes stay
    in nodes.py but are no longer wired onto this composed path.)"""
    g = StateGraph(AgentState)

    g.add_node("guard_input", guard_input)
    g.add_node("load_dataset", load_dataset)
    g.add_node("propose_code", propose_code)
    g.add_node("execute_code", execute_code)
    g.add_node("explain_result", explain_result)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("guard_input")
    g.add_conditional_edges(
        "guard_input",
        lambda s: "handle_error" if s.get("error") else "load_dataset",
        {"handle_error": "handle_error", "load_dataset": "load_dataset"},
    )
    g.add_conditional_edges(
        "load_dataset",
        lambda s: "handle_error" if s.get("error") else "propose_code",
        {"handle_error": "handle_error", "propose_code": "propose_code"},
    )
    g.add_conditional_edges(
        "propose_code",
        lambda s: "handle_error" if s.get("error") else "execute_code",
        {"handle_error": "handle_error", "execute_code": "execute_code"},
    )
    g.add_conditional_edges(
        "execute_code",
        after_execute,
        {"propose_code": "propose_code", "explain_result": "explain_result",
         "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "explain_result",
        lambda s: "handle_error" if s.get("error") else "finalize",
        {"handle_error": "handle_error", "finalize": "finalize"},
    )
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


def _build_legacy_graph() -> StateGraph:
    """The pre-analysis transform/react seam graph. Superseded on the main
    composed path but kept intact behind `run_agent` so the prior-phase LLM-client
    / routing gate (which exercises a bare model call, no dataset) keeps working.
    """
    g = StateGraph(AgentState)
    g.add_node("guard_input", guard_input)
    g.add_node("load_memory", load_memory)
    g.add_node("react", react)
    g.add_node("guard_output", guard_output)
    g.add_node("write_memory", write_memory)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("guard_input")
    g.add_conditional_edges(
        "guard_input",
        lambda s: "handle_error" if s.get("error") else "load_memory",
        {"handle_error": "handle_error", "load_memory": "load_memory"},
    )
    g.add_edge("load_memory", "react")
    g.add_conditional_edges(
        "react", after_react,
        {"react": "react", "handle_error": "handle_error", "guard_output": "guard_output"},
    )
    g.add_conditional_edges(
        "guard_output",
        lambda s: "handle_error" if s.get("error") else "write_memory",
        {"handle_error": "handle_error", "write_memory": "write_memory"},
    )
    g.add_edge("write_memory", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


# Exported compiled graph — name kept as `agentic_ai` so runner imports keep working.
agentic_ai = _build_graph()

# Legacy transform/react graph behind run_agent (off the analysis path).
legacy_agentic_ai = _build_legacy_graph()
