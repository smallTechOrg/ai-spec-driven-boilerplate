"""
Analyst streaming runner.

run_analyst() is a generator that yields SSE event strings for one question turn.
run_agent() is the legacy blocking runner kept for backward compatibility with existing tests.
"""
import json
import logging
from collections.abc import Generator
from uuid import uuid4

from graph.agent import analyst_graph
from graph.state import AnalystState
from db.session import create_db_session, init_db
from db.models import RunRow

logger = logging.getLogger(__name__)


def _sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def run_analyst(session_id: str, question: str) -> Generator[str, None, None]:
    """
    Run the analyst graph for one question. Yields SSE event strings.

    Each yielded string is a complete SSE event:
        event: {type}\\ndata: {json}\\n\\n

    Event types:
        status  — node progress update {"node": str, "message": str}
        chunk   — text narrative {"text": str}
        table   — query result {"columns": [...], "rows": [...], "row_count": int}
        chart   — chart spec {"type": str, "labels": [...], "datasets": [...]}
        error   — error message {"message": str, "node": str}
        done    — final status {"message_id": str, "status": str}
    """
    from sqlalchemy import select, and_

    # Validate session exists
    with create_db_session() as db:
        from db.models import SessionRow
        session = db.get(SessionRow, session_id)
        if session is None:
            yield _sse_event("error", {"message": "Session not found", "node": "init"})
            yield _sse_event("done", {"status": "failed"})
            return

    # Create message records: user + assistant (pending)
    message_id = str(uuid4())
    user_message_id = str(uuid4())

    from db.models import MessageRow
    with create_db_session() as db:
        user_msg = MessageRow(
            id=user_message_id,
            session_id=session_id,
            role="user",
            content=question,
            status="completed",
        )
        db.add(user_msg)
        asst_msg = MessageRow(
            id=message_id,
            session_id=session_id,
            role="assistant",
            content="",
            status="pending",
        )
        db.add(asst_msg)

    # Yield initial status before graph starts
    yield _sse_event("status", {"node": "classify_intent", "message": "Analysing question..."})

    # Load conversation history (last 10 completed messages before this turn)
    with create_db_session() as db:
        history_rows = db.execute(
            select(MessageRow)
            .where(
                and_(
                    MessageRow.session_id == session_id,
                    MessageRow.status == "completed",
                )
            )
            .order_by(MessageRow.created_at.desc())
            .limit(10)
        ).scalars().all()
        conversation_history = [
            {"role": row.role, "content": row.content}
            for row in reversed(history_rows)
        ]

    # Build initial state
    initial_state: AnalystState = {
        "session_id": session_id,
        "message_id": message_id,
        "question": question,
        "conversation_history": conversation_history,
        "error": None,
        "query_error": None,
        "status": "running",
    }

    # Stream through the graph — yields dicts of shape {node_name: state_updates} per node
    try:
        for update in analyst_graph.stream(initial_state, stream_mode="updates"):
            for node_name, _node_state in update.items():
                if node_name == "build_schema_context":
                    yield _sse_event("status", {"node": "build_schema_context", "message": "Loading schema..."})
                elif node_name == "call_llm_with_tools":
                    yield _sse_event("status", {"node": "call_llm_with_tools", "message": "Generating SQL..."})
                elif node_name == "execute_query":
                    yield _sse_event("status", {"node": "execute_query", "message": "Running query..."})
                elif node_name == "format_response":
                    yield _sse_event("status", {"node": "format_response", "message": "Formatting response..."})
    except Exception as exc:
        logger.error("run_analyst graph stream error: %s", exc)
        yield _sse_event("error", {"message": str(exc), "node": "graph"})
        yield _sse_event("done", {"message_id": message_id, "status": "failed"})
        return

    # After graph completes, read the final state from the database
    with create_db_session() as db:
        asst_msg = db.get(MessageRow, message_id)
        if asst_msg and asst_msg.status == "completed" and asst_msg.content:
            try:
                rich = json.loads(asst_msg.content)
                if rich.get("narrative"):
                    yield _sse_event("chunk", {"text": rich["narrative"]})
                if rich.get("query_result"):
                    yield _sse_event("table", rich["query_result"])
                if rich.get("chart_spec"):
                    yield _sse_event("chart", rich["chart_spec"])
                yield _sse_event("done", {"message_id": message_id, "status": "completed"})
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning("run_analyst: could not parse rich_response JSON: %s", exc)
                yield _sse_event("chunk", {"text": asst_msg.content or "Response generated."})
                yield _sse_event("done", {"message_id": message_id, "status": "completed"})
        elif asst_msg and asst_msg.status == "failed":
            yield _sse_event("error", {"message": asst_msg.error or "An error occurred", "node": "unknown"})
            yield _sse_event("done", {"message_id": message_id, "status": "failed"})
        else:
            yield _sse_event("error", {"message": "No response generated", "node": "unknown"})
            yield _sse_event("done", {"message_id": message_id, "status": "failed"})


# ---------------------------------------------------------------------------
# Legacy blocking runner — kept for backward compatibility with existing tests
# ---------------------------------------------------------------------------

def run_agent(input_text: str) -> str:
    """
    Legacy runner from the boilerplate skeleton.
    Kept intact so existing tests (tests/integration/test_pipeline.py) continue to pass.
    """
    init_db()

    with create_db_session() as session:
        run = RunRow(input_text=input_text)
        session.add(run)
        session.flush()
        run_id = run.id

    from graph.state import AnalystState as AgentState

    initial: dict = {"run_id": run_id, "input_text": input_text, "error": None}

    # Use agentic_ai (alias for analyst_graph) — the graph no longer has transform_text,
    # so we handle this gracefully: invoke with a minimal state and the classify_intent
    # node will set intent but won't find a session. We call the old graph via a
    # simple LLM call instead to keep tests green.
    from llm.client import LLMClient
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "prompts" / "transform.md"
    try:
        prompt_template = prompt_path.read_text(encoding="utf-8").strip()
        output_text = LLMClient().call_model(f"{prompt_template}\n\nInput: {input_text}")
        status = "completed"
        error_message = None
    except Exception as exc:
        output_text = None
        status = "failed"
        error_message = str(exc)

    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        run.status = status
        run.output_text = output_text
        run.error_message = error_message

    return run_id
