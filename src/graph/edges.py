"""Conditional routing for the CSV-analysis pipeline.

Each work node routes to ``handle_error`` when ``state["error"]`` is set,
otherwise to the next node on the single answer path.
"""

from graph.state import AgentState


def after_load_profile(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "build_prompt"


def after_build_prompt(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "answer"


def after_answer(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "finalize"
