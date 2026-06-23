"""Unit tests for analyst graph edge functions."""
from graph.edges import after_classify, after_schema, after_llm, after_execute, after_format


def test_after_classify_error():
    state = {"error": "something went wrong"}
    assert after_classify(state) == "handle_error"


def test_after_classify_off_topic():
    state = {"intent": "off_topic", "error": None}
    assert after_classify(state) == "format_response"


def test_after_classify_clarification():
    state = {"intent": "clarification", "error": None}
    assert after_classify(state) == "format_response"


def test_after_classify_data_query():
    state = {"intent": "data_query", "error": None}
    assert after_classify(state) == "build_schema_context"


def test_after_classify_unknown_intent_goes_to_build_schema():
    # If intent is something unexpected (not off_topic/clarification), default to schema
    state = {"intent": "data_query", "error": None}
    assert after_classify(state) == "build_schema_context"


def test_after_schema_error():
    state = {"error": "No datasets"}
    assert after_schema(state) == "handle_error"


def test_after_schema_success():
    state = {"error": None, "schema_context": "Dataset: sales"}
    assert after_schema(state) == "call_llm_with_tools"


def test_after_llm_error():
    state = {"error": "API error"}
    assert after_llm(state) == "handle_error"


def test_after_llm_with_sql():
    state = {"error": None, "sql": "SELECT * FROM sales"}
    assert after_llm(state) == "execute_query"


def test_after_llm_no_sql():
    state = {"error": None, "sql": None}
    assert after_llm(state) == "format_response"


def test_after_execute_query_error():
    state = {"query_error": "column not found"}
    assert after_execute(state) == "handle_error"


def test_after_execute_success():
    state = {"query_error": None, "query_result": {"columns": [], "rows": [], "row_count": 0}}
    assert after_execute(state) == "format_response"


def test_after_format_error():
    state = {"error": "format failed"}
    assert after_format(state) == "handle_error"


def test_after_format_success():
    state = {"error": None, "rich_response": {"narrative": "ok"}}
    assert after_format(state) == "finalize"
