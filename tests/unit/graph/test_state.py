"""Unit tests for AnalystState TypedDict."""


def test_analyst_state_is_total_false():
    """AnalystState should be constructible with partial keys."""
    from graph.state import AnalystState

    state: AnalystState = {
        "session_id": "abc",
        "question": "How many rows?",
    }
    assert state["session_id"] == "abc"
    assert state["question"] == "How many rows?"
    # Optional keys absent — no error
    assert state.get("intent") is None
    assert state.get("sql") is None


def test_analyst_state_full():
    """AnalystState can hold all defined keys."""
    from graph.state import AnalystState

    state: AnalystState = {
        "session_id": "s1",
        "message_id": "m1",
        "question": "What is the total revenue?",
        "conversation_history": [{"role": "user", "content": "hi"}],
        "intent": "data_query",
        "schema_context": "Dataset: sales (100 rows)",
        "datasets": [{"name": "sales.csv", "file_path": "/tmp/sales.csv"}],
        "sql": "SELECT SUM(revenue) FROM sales",
        "query_result": {"columns": ["sum(revenue)"], "rows": [[1000]], "row_count": 1},
        "query_log_id": "log-1",
        "narrative": "Total revenue is $1000.",
        "chart_spec": None,
        "rich_response": {"narrative": "Total revenue is $1000."},
        "error": None,
        "query_error": None,
        "status": "completed",
    }
    assert state["intent"] == "data_query"
    assert state["sql"] == "SELECT SUM(revenue) FROM sales"
    assert state["status"] == "completed"
