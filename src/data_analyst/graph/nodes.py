from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from data_analyst.graph.state import AgentState

log = logging.getLogger(__name__)

_dataframe_store: dict[str, pd.DataFrame] = {}


def _release_df(session_id: str) -> None:
    _dataframe_store.pop(session_id, None)


def setup(state: AgentState) -> AgentState:
    session_id = state["session_id"]
    dataset_path = state.get("dataset_path", "")

    path = Path(dataset_path)
    if not path.exists():
        return {**state, "error": f"Dataset file not found: {dataset_path}"}

    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        elif path.suffix.lower() == ".json":
            df = pd.read_json(path)
        else:
            return {**state, "error": f"Unsupported file type: {path.suffix}"}
    except Exception as exc:
        return {**state, "error": f"Failed to parse file: {exc}"}

    _dataframe_store[session_id] = df
    return {
        **state,
        "dataframe_key": session_id,
        "action_history": [],
        "iteration_count": 0,
        "tokens_input": 0,
        "tokens_output": 0,
        "estimated_cost_usd": 0.0,
        "error": None,
    }


def plan_action(state: AgentState) -> AgentState:
    from data_analyst.llm.client import get_llm_client

    session_id = state["session_id"]
    df = _dataframe_store.get(session_id)
    if df is None:
        return {**state, "error": "DataFrame not found in store — session may have expired"}

    schema_info = {
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "shape": list(df.shape),
        "sample": df.head(3).to_dict(orient="records"),
    }

    history_text = "\n".join(
        f"Step {i + 1}: ACTION: {entry['action']}\nResult: {entry['result']}"
        + (" [ERROR]" if entry.get("is_error") else "")
        for i, entry in enumerate(state.get("action_history", []))
    )

    prompt = f"""You are a data analysis assistant. You have access to a pandas DataFrame.

Dataset schema:
{json.dumps(schema_info, indent=2)}

User question: {state.get("user_question", "")}

Previous steps:
{history_text or "None yet."}

Instructions:
- Output exactly one pandas operation as a method-call suffix (the part after "df."), tagged as: ACTION: <operation>
- Do NOT include "df." in your action.
- When you have enough information to answer the question, output: FINAL ANSWER: <your complete answer>
- Do not include any other text besides ACTION: or FINAL ANSWER:

<node:plan>
What is your next action or final answer?"""

    client = get_llm_client()
    try:
        response = client.generate(prompt)
    except Exception as exc:
        return {**state, "error": f"LLM API error: {exc}"}

    usage = getattr(response, "usage", None)
    tokens_in = state.get("tokens_input", 0)
    tokens_out = state.get("tokens_output", 0)
    if usage:
        tokens_in += getattr(usage, "prompt_token_count", 0) or 0
        tokens_out += getattr(usage, "candidates_token_count", 0) or 0

    return {
        **state,
        "llm_response": response.text if hasattr(response, "text") else str(response),
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
    }


def execute_action(state: AgentState) -> AgentState:
    from data_analyst.tools.pandas_executor import validate_and_execute

    session_id = state["session_id"]
    df = _dataframe_store.get(session_id)
    llm_response = state.get("llm_response", "")

    action_line = ""
    for line in llm_response.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("ACTION:"):
            action_line = stripped[len("ACTION:"):].strip()
            break

    if not action_line:
        action_line = llm_response.strip()

    result_str, is_error = validate_and_execute(action_line, df)

    history = list(state.get("action_history", []))
    history.append({"action": action_line, "result": result_str, "is_error": is_error})

    return {
        **state,
        "action_history": history,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


def finalize(state: AgentState) -> AgentState:
    _release_df(state.get("session_id", ""))

    response = state.get("llm_response", "")
    idx = response.upper().find("FINAL ANSWER:")
    answer = response[idx + len("FINAL ANSWER:"):].strip() if idx >= 0 else response.strip()

    _persist_run(state, status="completed", final_answer=answer)
    return {**state, "final_answer": answer}


def force_finalize(state: AgentState) -> AgentState:
    _release_df(state.get("session_id", ""))

    history = state.get("action_history", [])
    n = state.get("iteration_count", 0)

    from data_analyst.llm.client import get_llm_client
    client = get_llm_client()
    synthesis_prompt = f"""You are a data analysis assistant. You ran {n} analysis steps but could not reach a complete answer.

Steps taken:
{json.dumps(history, indent=2)}

User question: {state.get("user_question", "")}

<node:force_finalize>
Synthesise the best answer you can from the steps above. Start with a concrete finding. Note what could not be determined.
"""
    try:
        response = client.generate(synthesis_prompt)
        answer = response.text if hasattr(response, "text") else str(response)
    except Exception:
        findings = "; ".join(
            f"Step {i + 1}: {e['action']} → {e['result'][:100]}"
            for i, e in enumerate(history)
        )
        answer = (
            f"Analysis incomplete after {n} iterations. "
            f"Findings so far: {findings or 'no steps completed.'}"
        )

    _persist_run(
        state,
        status="completed",
        final_answer=answer,
        error_message="iteration_limit_reached",
    )
    return {**state, "final_answer": answer}


def handle_error(state: AgentState) -> AgentState:
    _release_df(state.get("session_id", ""))
    error = state.get("error", "Unknown error")
    log.error("agent.fatal_error", extra={"run_id": state.get("run_id"), "error": error})
    _persist_run(state, status="failed", error_message=error)
    return state


def _persist_run(
    state: AgentState,
    *,
    status: str,
    final_answer: str | None = None,
    error_message: str | None = None,
) -> None:
    from datetime import datetime, timezone
    from data_analyst.db.session import create_db_session
    from data_analyst.db.models import RunRow

    run_id = state.get("run_id")
    if not run_id:
        return
    try:
        with create_db_session() as session:
            run = session.get(RunRow, run_id)
            if run:
                run.status = status
                run.final_answer = final_answer
                run.action_history = json.dumps(state.get("action_history", []))
                run.tokens_input = state.get("tokens_input", 0)
                run.tokens_output = state.get("tokens_output", 0)
                run.estimated_cost_usd = str(state.get("estimated_cost_usd") or 0.0)
                run.error_message = error_message
                run.completed_at = datetime.now(timezone.utc)
    except Exception as exc:
        log.warning("agent.persist_run_failed", extra={"run_id": run_id, "error": str(exc)})
