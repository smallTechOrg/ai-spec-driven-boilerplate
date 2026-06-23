"""
Integration tests for the analyst graph.

These tests run the real LLM (Gemini) with actual CSV data.
Requires AGENT_GEMINI_API_KEY in .env.
"""
import json
import os
import tempfile
import pytest
from sqlalchemy.orm import Session


@pytest.mark.usefixtures("_require_llm_key")
def test_classify_intent_real_llm(_isolated_db):
    """classify_intent makes a real Gemini call and returns a valid label."""
    from graph.nodes import classify_intent

    state = {
        "session_id": "s1",
        "question": "What is the total revenue by region?",
    }
    result = classify_intent(state)

    assert result.get("error") is None
    assert result["intent"] in ("data_query", "clarification", "off_topic")


@pytest.mark.usefixtures("_require_llm_key")
def test_full_analyst_graph_data_query(_isolated_db):
    """
    Full graph run: upload a CSV → ask a data question → verify completed message in DB.
    """
    from db.models import SessionRow, DatasetRow, MessageRow
    from graph.agent import analyst_graph

    # Write a temp CSV
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, prefix="test_sales_"
    ) as f:
        f.write("region,revenue\nNorth,500\nSouth,300\nEast,700\n")
        csv_path = f.name

    try:
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Test Session")
            s.add(sess)
            s.commit()
            session_id = sess.id

            ds = DatasetRow(
                session_id=session_id,
                name="sales.csv",
                file_path=csv_path,
                file_type="csv",
                row_count=3,
                columns_json=json.dumps([
                    {"name": "region", "type": "VARCHAR"},
                    {"name": "revenue", "type": "DOUBLE"},
                ]),
            )
            s.add(ds)

            msg = MessageRow(
                session_id=session_id,
                role="assistant",
                content="",
                status="pending",
            )
            s.add(msg)
            s.commit()
            message_id = msg.id

        initial_state = {
            "session_id": session_id,
            "message_id": message_id,
            "question": "What is the total revenue across all regions?",
            "conversation_history": [],
            "error": None,
            "query_error": None,
            "status": "running",
        }

        final_state = analyst_graph.invoke(initial_state)

        assert final_state.get("error") is None
        assert final_state["status"] == "completed"
        assert final_state.get("rich_response") is not None

        rich = final_state["rich_response"]
        assert rich.get("narrative")
        # Should have run SQL and got a result
        assert rich.get("query_result") is not None

        # Check message persisted to DB
        with Session(_isolated_db) as s:
            msg = s.get(MessageRow, message_id)
            assert msg.status == "completed"
            persisted = json.loads(msg.content)
            assert persisted.get("narrative")

    finally:
        os.unlink(csv_path)


@pytest.mark.usefixtures("_require_llm_key")
def test_analyst_graph_no_datasets(_isolated_db):
    """Graph routes to handle_error when session has no datasets."""
    from db.models import SessionRow, MessageRow
    from graph.agent import analyst_graph

    with Session(_isolated_db) as s:
        sess = SessionRow(name="Empty Session")
        s.add(sess)
        s.commit()
        session_id = sess.id

        msg = MessageRow(
            session_id=session_id,
            role="assistant",
            content="",
            status="pending",
        )
        s.add(msg)
        s.commit()
        message_id = msg.id

    initial_state = {
        "session_id": session_id,
        "message_id": message_id,
        "question": "What is the total revenue?",
        "conversation_history": [],
        "error": None,
        "query_error": None,
        "status": "running",
    }

    final_state = analyst_graph.invoke(initial_state)

    # Should fail because there are no datasets
    assert final_state["status"] == "failed"

    with Session(_isolated_db) as s:
        msg = s.get(MessageRow, message_id)
        assert msg.status == "failed"
        assert msg.error is not None


@pytest.mark.usefixtures("_require_llm_key")
def test_run_analyst_streaming(_isolated_db):
    """run_analyst yields SSE events for a question with real LLM and real CSV."""
    import tempfile
    import os
    from db.models import SessionRow, DatasetRow
    from graph.runner import run_analyst

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, prefix="test_rev_"
    ) as f:
        f.write("product,sales\nWidgetA,100\nWidgetB,250\n")
        csv_path = f.name

    try:
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Stream Test")
            s.add(sess)
            s.commit()
            session_id = sess.id

            ds = DatasetRow(
                session_id=session_id,
                name="products.csv",
                file_path=csv_path,
                file_type="csv",
                row_count=2,
                columns_json=json.dumps([
                    {"name": "product", "type": "VARCHAR"},
                    {"name": "sales", "type": "INTEGER"},
                ]),
            )
            s.add(ds)
            s.commit()

        events = list(run_analyst(session_id, "Which product has the highest sales?"))

        # Must yield at least one status and one done event
        event_types = []
        for event_str in events:
            for line in event_str.strip().split("\n"):
                if line.startswith("event: "):
                    event_types.append(line[len("event: "):].strip())

        assert "done" in event_types
        # Should not be all errors
        done_events = [e for e in events if "event: done" in e]
        assert done_events
        done_data = json.loads(done_events[-1].split("data: ", 1)[1].strip())
        assert done_data.get("status") == "completed"

    finally:
        os.unlink(csv_path)
