"""Graph runner — entry point for invoking the Data Analysis Agent."""

from __future__ import annotations

import os
from uuid import uuid4

import structlog

from graph.agent import agentic_ai
from graph.state import AgentState

log = structlog.get_logger("agent.runner")


def run_agent(file_id: str, question: str, session_id: str | None = None) -> dict:
    """
    Invoke the LangGraph agent for a given file + question.

    Returns:
        {
            "run_id": str,
            "answer": str | None,
            "answer_text": str | None,
            "chart_spec": dict | None,
            "status": str,
            "error": str | None,
        }
    """
    # Ensure LangSmith env vars are forwarded if available via Settings
    try:
        from config.settings import get_settings
        s = get_settings()
        if getattr(s, "langchain_api_key", ""):
            os.environ.setdefault("LANGCHAIN_API_KEY", s.langchain_api_key)
        if getattr(s, "langchain_tracing_v2", ""):
            os.environ.setdefault("LANGCHAIN_TRACING_V2", s.langchain_tracing_v2)
    except Exception:  # noqa: BLE001
        pass

    run_id = str(uuid4())
    log.info("run_start", run_id=run_id, file_id=file_id, question=question[:100])

    initial: AgentState = {
        "run_id": run_id,
        "file_id": file_id,
        "question": question,
        "session_id": session_id,
        "source_type": "csv",
        "error": None,
        "conversation_history": [],
    }

    final = agentic_ai.invoke(initial)

    answer = final.get("answer_text")
    return {
        "run_id": run_id,
        "answer": answer,
        "answer_text": answer,
        "chart_spec": final.get("chart_spec"),
        "status": final.get("status", "completed"),
        "error": final.get("error"),
    }


def run_agent_text(input_text: str) -> str:
    """
    Backward-compatible wrapper for the skeleton /runs endpoint.
    Creates a run that transforms text; retained for backward compat only.
    """
    from db.session import init_db, create_db_session
    from db.models import RunRow
    from graph.agent import agentic_ai as _graph

    init_db()

    # Build a minimal state that will trigger the error path gracefully
    # (no file_id means load_dataset will set error, handle_error will persist)
    run_id_local = str(uuid4())

    with create_db_session() as session:
        run = RunRow(id=run_id_local, input_text=input_text)
        session.add(run)

    # For the old /runs endpoint we directly call the LLM inline
    try:
        from llm.client import LLMClient
        result_text = LLMClient().call_model(input_text)
    except Exception as exc:  # noqa: BLE001
        result_text = None
        error_msg = str(exc)
    else:
        error_msg = None

    with create_db_session() as session:
        run = session.get(RunRow, run_id_local)
        if run:
            run.status = "completed" if error_msg is None else "failed"
            run.output_text = result_text
            run.error_message = error_msg

    return run_id_local
