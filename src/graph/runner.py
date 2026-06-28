"""Entry point that wires the API to the agent graph.

Creates/loads the conversation, records the user turn, persists a pending run
row, invokes the graph, and returns the api.md `/ask` payload shape.
"""
from __future__ import annotations

from db.models import ConversationRow, DatasetRow, MessageRow, RunRow
from db.session import create_db_session
from graph.agent import agentic_ai
from graph.state import AgentState


class DatasetNotFound(Exception):
    pass


def run_agent(dataset_id: str, question: str, conversation_id: str | None = None) -> dict:
    """Run one analysis turn. Returns the `/ask` response payload dict.

    Raises DatasetNotFound if the dataset does not exist.
    """
    with create_db_session() as session:
        ds = session.get(DatasetRow, dataset_id)
        if ds is None:
            raise DatasetNotFound(dataset_id)

        # Create or validate the conversation (memory scope).
        if conversation_id:
            conv = session.get(ConversationRow, conversation_id)
            if conv is None:
                conv = ConversationRow(id=conversation_id, dataset_id=dataset_id)
                session.add(conv)
                session.flush()
        else:
            conv = ConversationRow(dataset_id=dataset_id)
            session.add(conv)
            session.flush()
        conv_id = conv.id

        # Record the user turn.
        session.add(MessageRow(conversation_id=conv_id, role="user", content=question))

        # Persist a pending run row.
        run = RunRow(
            dataset_id=dataset_id,
            conversation_id=conv_id,
            question=question,
            status="pending",
        )
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AgentState = {
        "run_id": run_id,
        "conversation_id": conv_id,
        "dataset_id": dataset_id,
        "question": question,
        "iteration": 0,
        "error": None,
    }
    final = agentic_ai.invoke(initial)

    status = final.get("status", "completed")
    execution = final.get("execution") or {}
    tokens = final.get("tokens") or {"prompt": 0, "completion": 0}

    return {
        "run_id": run_id,
        "conversation_id": conv_id,
        "status": status,
        "answer": final.get("answer"),
        "plan": final.get("plan"),
        "code": final.get("code"),
        "result_preview": execution.get("result_preview"),
        "iterations": final.get("iteration", 0),
        "suggestions": final.get("suggestions", []),
        "chart_spec": final.get("chart_spec"),  # P1: None
        "clarifying_question": final.get("clarifying_question"),  # P1: None
        "tokens": {
            "prompt": int(tokens.get("prompt", 0) or 0),
            "completion": int(tokens.get("completion", 0) or 0),
        },
        "cost_usd": float(final.get("cost_usd", 0.0) or 0.0),
        "error_message": final.get("error"),
    }
