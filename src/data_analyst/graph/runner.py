from __future__ import annotations

import json
from datetime import datetime, timezone

from data_analyst.graph.agent import agent_graph
from data_analyst.graph.nodes import _dataframe_store
from data_analyst.graph.state import AgentState
from data_analyst.db.session import create_db_session, init_db
from data_analyst.db.models import RunRow


def run_agent(
    session_id: str,
    run_id: str,
    dataset_path: str,
    user_question: str,
) -> dict:
    initial: AgentState = {
        "run_id": run_id,
        "session_id": session_id,
        "dataset_path": dataset_path,
        "user_question": user_question,
        "action_history": [],
        "iteration_count": 0,
        "tokens_input": 0,
        "tokens_output": 0,
        "estimated_cost_usd": 0.0,
        "error": None,
        "final_answer": None,
        "llm_response": "",
    }

    try:
        final_state = agent_graph.invoke(initial)
    finally:
        _dataframe_store.pop(session_id, None)

    return final_state
