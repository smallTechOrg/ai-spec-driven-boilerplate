"""Runner that bridges the API route, the LangGraph graph, and the DB.

``run_ask`` loads the Dataset + prior conversation history from SQLite, builds
the graph's initial state, invokes ``agentic_ai``, persists the resulting Turn
(completed OR failed), and returns the response ``data`` dict shaped exactly to
``spec/api.md`` (and the frontend contract in ``frontend/src/lib/api.ts``).

The privacy boundary lives downstream (``llm/context.py``); this layer only
moves profile/sample/history into the state — never raw rows.
"""

from __future__ import annotations

from typing import Callable

from db.models import Conversation, Dataset, Turn
from db.session import create_db_session
from graph.agent import agentic_ai

# History fed back to the LLM is truncated to the last K turns (see spec/agent.md
# "Context window management"). Keeps the prompt bounded for follow-ups.
HISTORY_LIMIT = 6


class DatasetNotFound(Exception):
    """Raised when an ask targets a dataset id that does not exist."""


def _result_table_rows(result_table) -> list:
    """Map the graph's {columns, rows, row_count} into the bare rows array the
    contract/frontend expect. Tolerates a bare list or None."""
    if result_table is None:
        return []
    if isinstance(result_table, list):
        return result_table
    if isinstance(result_table, dict):
        rows = result_table.get("rows")
        return rows if isinstance(rows, list) else []
    return []


def _build_response(turn_id: str, conversation_id: str, final: dict) -> dict:
    prompt = int(final.get("prompt_tokens") or 0)
    completion = int(final.get("completion_tokens") or 0)
    return {
        "turn_id": turn_id,
        "conversation_id": conversation_id,
        "answer": final.get("answer") or "",
        "plan": final.get("plan") or [],
        "code": final.get("code") or "",
        "result_table": _result_table_rows(final.get("result_table")),
        "chart_spec": final.get("chart_spec"),
        "follow_ups": final.get("follow_ups") or [],
        "token_usage": {
            "prompt": prompt,
            "completion": completion,
            "total": prompt + completion,
        },
        "estimated_cost_usd": float(final.get("estimated_cost_usd") or 0.0),
        "assumptions": final.get("assumptions") or [],
    }


def run_ask(
    dataset_id: str,
    conversation_id: str | None,
    question: str,
    on_step: Callable[[str, str], None] | None = None,
) -> dict:
    """Run one analysis turn end-to-end and persist it.

    Returns the response ``data`` dict. Raises ``DatasetNotFound`` if the
    dataset id is unknown. Graph failures DO NOT raise — they persist a failed
    Turn and return a response whose ``answer`` carries the readable error.
    """
    # --- Load context from the DB (profile/sample/history only) ---
    with create_db_session() as session:
        dataset = session.get(Dataset, dataset_id)
        if dataset is None:
            raise DatasetNotFound(dataset_id)

        if conversation_id:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None or conversation.dataset_id != dataset_id:
                # Unknown/mismatched id → start a fresh conversation for safety.
                conversation = Conversation(dataset_id=dataset_id)
                session.add(conversation)
                session.flush()
        else:
            conversation = Conversation(
                dataset_id=dataset_id, title=(question[:80] or None)
            )
            session.add(conversation)
            session.flush()
        conversation_id = conversation.id

        prior = (
            session.query(Turn)
            .filter(Turn.conversation_id == conversation_id)
            .order_by(Turn.created_at.asc())
            .all()
        )
        history = [
            {"question": t.question, "answer": t.answer or ""}
            for t in prior
            if t.status == "completed"
        ][-HISTORY_LIMIT:]

        # Create the Turn row up-front so run_id == turn id (graph state identity).
        turn = Turn(
            conversation_id=conversation_id,
            question=question,
            status="completed",
        )
        session.add(turn)
        session.flush()
        turn_id = turn.id

        initial = {
            "run_id": turn_id,
            "dataset_id": dataset_id,
            "conversation_id": conversation_id,
            "question": question,
            "profile": dataset.profile or [],
            "sample_rows": dataset.sample_rows or [],
            "row_count": dataset.row_count,
            "file_path": dataset.file_path,
            "history": history,
            "error": None,
        }
        if on_step is not None:
            initial["on_step"] = on_step

    # --- Invoke the graph (LLM + local execution) outside the DB session ---
    final = agentic_ai.invoke(initial)

    status = final.get("status") or ("failed" if final.get("error") else "completed")

    # --- Persist the finished Turn ---
    with create_db_session() as session:
        turn = session.get(Turn, turn_id)
        turn.plan = final.get("plan") or []
        turn.code = final.get("code") or ""
        rt = final.get("result_table")
        turn.result_table = rt if isinstance(rt, dict) else {"rows": _result_table_rows(rt)}
        turn.answer = final.get("answer") or ""
        turn.chart_spec = final.get("chart_spec")
        turn.follow_ups = final.get("follow_ups") or []
        turn.prompt_tokens = int(final.get("prompt_tokens") or 0)
        turn.completion_tokens = int(final.get("completion_tokens") or 0)
        turn.estimated_cost_usd = float(final.get("estimated_cost_usd") or 0.0)
        turn.status = status
        turn.error_message = final.get("error")

    return _build_response(turn_id, conversation_id, final)
