from typing import Any, Generator

import pandas as pd

from datachat.graph.agent import agent_graph
from datachat.graph.nodes import _dataframe_store
from datachat.graph.state import AgentState
from datachat.db.session import create_db_session
from datachat.db.models import RunRow


def _make_run(session_id: str) -> str:
    with create_db_session() as db:
        run = RunRow(session_id=session_id)
        db.add(run)
        db.flush()
        return run.id


def run_agent(session_id: str, question: str, df: pd.DataFrame) -> dict[str, Any]:
    """Synchronous run — returns full result when done. Used by the non-streaming endpoint."""
    _dataframe_store[session_id] = df
    run_id = _make_run(session_id)
    initial: AgentState = {"run_id": run_id, "session_id": session_id, "question": question}
    final = agent_graph.invoke(initial)

    from datachat.config.settings import get_settings
    return {
        "answer": final.get("final_answer", ""),
        "reasoning_trace": final.get("action_history", []),
        "llm_provider": get_settings().resolved_llm_provider,
        "run_id": run_id,
    }


def iter_agent_events(session_id: str, question: str, df: pd.DataFrame) -> Generator[dict, None, None]:
    """
    Stream typed events as the agent works through each step.

    Event types:
      {"type": "thinking"}                          — LLM is generating the next action
      {"type": "step", "description": str,          — one computation completed
              "result": str, "is_error": bool}
      {"type": "answer", "answer": str,             — final answer ready
              "reasoning_trace": list,
              "llm_provider": str}
      {"type": "error", "message": str}             — fatal failure
    """
    _dataframe_store[session_id] = df
    run_id = _make_run(session_id)
    initial: AgentState = {"run_id": run_id, "session_id": session_id, "question": question}

    prev_history_len = 0
    try:
        for chunk in agent_graph.stream(initial, stream_mode="updates"):
            for node_name, update in chunk.items():
                if node_name == "plan_action":
                    yield {"type": "thinking"}

                elif node_name == "execute_action":
                    history = update.get("action_history", [])
                    if len(history) > prev_history_len:
                        prev_history_len = len(history)
                        latest = history[-1]
                        yield {
                            "type": "step",
                            "description": latest.get("description", ""),
                            "result": latest.get("result", ""),
                            "is_error": latest.get("is_error", False),
                        }

                elif node_name in ("finalize", "force_finalize", "handle_error"):
                    from datachat.config.settings import get_settings
                    yield {
                        "type": "answer",
                        "answer": update.get("final_answer", ""),
                        "reasoning_trace": update.get("action_history", []),
                        "llm_provider": get_settings().resolved_llm_provider,
                    }

    except Exception as exc:
        yield {"type": "error", "message": str(exc)}
