"""Unit tests for analyst graph nodes (no LLM calls — use mocks)."""
import json
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# classify_intent
# ---------------------------------------------------------------------------

def test_classify_intent_data_query(monkeypatch):
    """classify_intent correctly classifies a data question."""
    mock_provider = MagicMock()
    mock_provider.call_model.return_value = "data_query"

    with patch("graph.nodes._get_provider", return_value=mock_provider):
        from graph.nodes import classify_intent
        state = {"question": "What is the total revenue?", "session_id": "s1"}
        result = classify_intent(state)

    assert result["intent"] == "data_query"
    assert result.get("error") is None


def test_classify_intent_off_topic(monkeypatch):
    mock_provider = MagicMock()
    mock_provider.call_model.return_value = "off_topic"

    with patch("graph.nodes._get_provider", return_value=mock_provider):
        from graph.nodes import classify_intent
        state = {"question": "Who won the World Cup?", "session_id": "s1"}
        result = classify_intent(state)

    assert result["intent"] == "off_topic"


def test_classify_intent_unknown_defaults_to_data_query(monkeypatch):
    """Unknown classification label defaults to data_query."""
    mock_provider = MagicMock()
    mock_provider.call_model.return_value = "UNKNOWN_GARBAGE_LABEL"

    with patch("graph.nodes._get_provider", return_value=mock_provider):
        from graph.nodes import classify_intent
        state = {"question": "something", "session_id": "s1"}
        result = classify_intent(state)

    assert result["intent"] == "data_query"


def test_classify_intent_api_error(monkeypatch):
    """classify_intent sets error on provider exception."""
    mock_provider = MagicMock()
    mock_provider.call_model.side_effect = RuntimeError("API timeout")

    with patch("graph.nodes._get_provider", return_value=mock_provider):
        from graph.nodes import classify_intent
        state = {"question": "x", "session_id": "s1"}
        result = classify_intent(state)

    assert result.get("error") is not None
    assert "API timeout" in result["error"]


# ---------------------------------------------------------------------------
# build_schema_context
# ---------------------------------------------------------------------------

def test_build_schema_context_no_datasets(_isolated_db):
    """build_schema_context sets error when session has no datasets."""
    from sqlalchemy.orm import Session
    from db.models import SessionRow

    # Create a session with no datasets
    with Session(_isolated_db) as s:
        sess = SessionRow(name="empty session")
        s.add(sess)
        s.commit()
        session_id = sess.id

    from graph.nodes import build_schema_context
    state = {"session_id": session_id, "question": "test"}
    result = build_schema_context(state)

    assert result.get("error") is not None
    assert "No datasets" in result["error"]


def test_build_schema_context_with_dataset(_isolated_db):
    """build_schema_context builds correct schema string from DB."""
    from sqlalchemy.orm import Session
    from db.models import SessionRow, DatasetRow

    columns_json = json.dumps([
        {"name": "id", "type": "INTEGER"},
        {"name": "name", "type": "VARCHAR"},
        {"name": "revenue", "type": "DOUBLE"},
    ])

    with Session(_isolated_db) as s:
        sess = SessionRow(name="test session")
        s.add(sess)
        s.commit()
        session_id = sess.id

        ds = DatasetRow(
            session_id=session_id,
            name="sales.csv",
            file_path="/data/sales.csv",
            file_type="csv",
            row_count=100,
            columns_json=columns_json,
        )
        s.add(ds)
        s.commit()

    from graph.nodes import build_schema_context
    state = {"session_id": session_id, "question": "test"}
    result = build_schema_context(state)

    assert result.get("error") is None
    assert "sales.csv" in result["schema_context"]
    assert "100 rows" in result["schema_context"]
    assert "revenue" in result["schema_context"]
    assert len(result["datasets"]) == 1
    assert result["datasets"][0]["name"] == "sales.csv"
    assert result["datasets"][0]["view_name"] == "sales"


# ---------------------------------------------------------------------------
# execute_query
# ---------------------------------------------------------------------------

def test_execute_query_success(_isolated_db):
    """execute_query runs SQL against an in-memory DuckDB and returns results."""
    import tempfile
    import os
    from sqlalchemy.orm import Session
    from db.models import SessionRow, MessageRow

    # Write a temp CSV
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("name,revenue\nAlice,100\nBob,200\n")
        csv_path = f.name

    try:
        with Session(_isolated_db) as s:
            sess = SessionRow(name="test")
            s.add(sess)
            s.commit()
            session_id = sess.id

            msg = MessageRow(session_id=session_id, role="assistant", content="", status="pending")
            s.add(msg)
            s.commit()
            message_id = msg.id

        from graph.nodes import execute_query
        state = {
            "session_id": session_id,
            "message_id": message_id,
            "sql": "SELECT name, revenue FROM sales ORDER BY name",
            "datasets": [
                {
                    "name": "sales.csv",
                    "file_path": csv_path,
                    "file_type": "csv",
                    "view_name": "sales",
                }
            ],
        }
        result = execute_query(state)

        assert result.get("query_error") is None
        qr = result["query_result"]
        assert "columns" in qr
        assert "name" in qr["columns"]
        assert "revenue" in qr["columns"]
        assert qr["row_count"] == 2
        assert result.get("query_log_id") is not None
    finally:
        os.unlink(csv_path)


def test_execute_query_sql_error(_isolated_db):
    """execute_query sets query_error on DuckDB failure."""
    from sqlalchemy.orm import Session
    from db.models import SessionRow, MessageRow

    with Session(_isolated_db) as s:
        sess = SessionRow(name="test")
        s.add(sess)
        s.commit()
        session_id = sess.id

        msg = MessageRow(session_id=session_id, role="assistant", content="", status="pending")
        s.add(msg)
        s.commit()
        message_id = msg.id

    from graph.nodes import execute_query
    state = {
        "session_id": session_id,
        "message_id": message_id,
        "sql": "SELECT * FROM nonexistent_table_xyz",
        "datasets": [],
    }
    result = execute_query(state)

    assert result.get("query_error") is not None


# ---------------------------------------------------------------------------
# format_response
# ---------------------------------------------------------------------------

def test_format_response_query_error():
    """format_response returns a user-friendly error message on query_error."""
    from graph.nodes import format_response
    state = {
        "query_error": "column 'foo' not found",
        "sql": "SELECT foo FROM bar",
        "intent": "data_query",
        "session_id": "s1",
        "message_id": "m1",
    }
    result = format_response(state)

    assert result.get("error") is None
    assert "error" in result["narrative"].lower() or "encountered" in result["narrative"].lower()
    assert result["chart_spec"] is None
    rich = result["rich_response"]
    assert rich["query_result"] is None
    assert rich["chart_spec"] is None


def test_format_response_off_topic_canned():
    """format_response returns canned response for off_topic questions."""
    from graph.nodes import format_response
    state = {
        "intent": "off_topic",
        "sql": None,
        "session_id": "s1",
        "message_id": "m1",
    }
    result = format_response(state)

    assert result.get("error") is None
    assert result["narrative"] is not None
    assert result["chart_spec"] is None


def test_format_response_with_existing_narrative():
    """format_response keeps existing narrative for clarification path."""
    from graph.nodes import format_response
    state = {
        "intent": "clarification",
        "sql": None,
        "narrative": "Could you rephrase your question?",
        "session_id": "s1",
        "message_id": "m1",
    }
    result = format_response(state)

    assert result["narrative"] == "Could you rephrase your question?"


def test_format_response_with_query_result(monkeypatch):
    """format_response calls LLM JSON mode for data_query results."""
    mock_provider = MagicMock()
    mock_provider.call_json.return_value = json.dumps({
        "narrative": "Revenue totalled $300.",
        "chart_type": "bar",
    })

    with patch("graph.nodes._get_provider", return_value=mock_provider):
        from graph.nodes import format_response
        state = {
            "intent": "data_query",
            "sql": "SELECT name, revenue FROM sales",
            "query_result": {
                "columns": ["name", "revenue"],
                "rows": [["Alice", 100], ["Bob", 200]],
                "row_count": 2,
            },
            "session_id": "s1",
            "message_id": "m1",
        }
        result = format_response(state)

    assert result.get("error") is None
    assert result["narrative"] == "Revenue totalled $300."
    assert result["chart_spec"] is not None
    assert result["chart_spec"]["type"] == "bar"
    rich = result["rich_response"]
    assert rich["narrative"] == "Revenue totalled $300."
    assert rich["query_result"] is not None


# ---------------------------------------------------------------------------
# handle_error
# ---------------------------------------------------------------------------

def test_handle_error_sets_status_failed(_isolated_db):
    """handle_error sets status=failed and persists error to DB."""
    from sqlalchemy.orm import Session
    from db.models import SessionRow, MessageRow
    from graph.nodes import handle_error

    with Session(_isolated_db) as s:
        sess = SessionRow(name="test")
        s.add(sess)
        s.commit()
        session_id = sess.id

        msg = MessageRow(session_id=session_id, role="assistant", content="", status="pending")
        s.add(msg)
        s.commit()
        message_id = msg.id

    state = {
        "session_id": session_id,
        "message_id": message_id,
        "error": "Something went wrong",
        "question": "test",
    }
    result = handle_error(state)

    assert result["status"] == "failed"

    with Session(_isolated_db) as s:
        msg = s.get(MessageRow, message_id)
        assert msg.status == "failed"
        assert msg.error == "Something went wrong"


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------

def test_finalize_sets_status_completed(_isolated_db):
    """finalize sets status=completed and persists rich_response to DB."""
    from sqlalchemy.orm import Session
    from db.models import SessionRow, MessageRow
    from graph.nodes import finalize

    with Session(_isolated_db) as s:
        sess = SessionRow(name="test")
        s.add(sess)
        s.commit()
        session_id = sess.id

        msg = MessageRow(session_id=session_id, role="assistant", content="", status="pending")
        s.add(msg)
        s.commit()
        message_id = msg.id

    rich_response = {
        "narrative": "Sales were $300.",
        "query_result": None,
        "chart_spec": None,
        "sql": "SELECT SUM(revenue) FROM sales",
        "query_log_id": None,
    }
    state = {
        "session_id": session_id,
        "message_id": message_id,
        "rich_response": rich_response,
        "question": "test",
    }
    result = finalize(state)

    assert result["status"] == "completed"

    with Session(_isolated_db) as s:
        msg = s.get(MessageRow, message_id)
        assert msg.status == "completed"
        parsed = json.loads(msg.content)
        assert parsed["narrative"] == "Sales were $300."


# ---------------------------------------------------------------------------
# domain models
# ---------------------------------------------------------------------------

def test_domain_models_importable():
    """All domain models import and instantiate correctly."""
    from domain.analyst import (
        ColumnSchema,
        QueryResultModel,
        ChartSpec,
        RichResponseModel,
        DatasetModel,
        MessageModel,
        SessionModel,
    )
    from datetime import datetime, timezone

    col = ColumnSchema(name="revenue", type="DOUBLE")
    assert col.name == "revenue"

    qr = QueryResultModel(columns=["name", "revenue"], rows=[["Alice", 100]], row_count=1)
    assert qr.row_count == 1

    chart = ChartSpec(type="bar", labels=["Alice", "Bob"], datasets=[{"label": "Revenue", "data": [100, 200]}])
    assert chart.type == "bar"

    rich = RichResponseModel(narrative="Revenue totalled $300.")
    assert rich.narrative == "Revenue totalled $300."
    assert rich.query_result is None

    now = datetime.now(timezone.utc)
    sess = SessionModel(session_id="s1", name="Session 1", created_at=now)
    assert sess.dataset_count == 0


# ---------------------------------------------------------------------------
# gemini provider extensions
# ---------------------------------------------------------------------------

def test_gemini_provider_has_call_with_tools():
    """GeminiProvider has the call_with_tools method."""
    from llm.providers.gemini import GeminiProvider
    assert hasattr(GeminiProvider, "call_with_tools")


def test_gemini_provider_has_call_json():
    """GeminiProvider has the call_json method."""
    from llm.providers.gemini import GeminiProvider
    assert hasattr(GeminiProvider, "call_json")


def test_analyst_graph_compiles():
    """analyst_graph is compiled and exported from graph.agent."""
    from graph.agent import analyst_graph
    assert analyst_graph is not None


def test_analyst_prompt_exists():
    """analyst.md prompt file exists and is non-empty."""
    from pathlib import Path
    prompt = Path("src/prompts/analyst.md")
    assert prompt.exists()
    assert len(prompt.read_text()) > 50
