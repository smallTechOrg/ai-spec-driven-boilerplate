import os
os.environ["ANALYST_LLM_PROVIDER"] = "stub"

import json
import duckdb
import pytest
from src.agent.graph import analyst_graph, respond_node
from src.db.schema import create_tables


@pytest.fixture
def mem_db_with_sales():
    conn = duckdb.connect(":memory:")
    create_tables(conn)
    conn.execute("""
        CREATE VIEW sales AS
        SELECT * FROM (VALUES
            ('widget', 100),
            ('gadget', 200),
            ('thingamajig', 150)
        ) t(product, revenue)
    """)
    yield conn
    conn.close()


class NonClosingConn:
    def __init__(self, inner): self._inner = inner
    def execute(self, *a, **kw): return self._inner.execute(*a, **kw)
    def close(self): pass


def make_mock_get_db(conn):
    def _get_db():
        return NonClosingConn(conn)
    return _get_db


def test_respond_node_chart_has_plotly_spec():
    state = {
        "question": "plot revenue over product",
        "session_id": "test", "datasets": [],
        "plan": "", "sql": "", "intent": "chart",
        "x_col": "product", "y_col": "revenue",
        "raw_rows": [["widget", 100], ["gadget", 200]],
        "columns": ["product", "revenue"], "response": {},
    }
    result = respond_node(state)
    r = result["response"]
    assert r["type"] == "chart"
    assert "plotly_spec" in r
    spec = r["plotly_spec"]
    assert "data" in spec
    assert spec["data"][0]["x"] == ["widget", "gadget"]
    assert spec["data"][0]["y"] == [100, 200]


def test_respond_node_chart_layout_has_title():
    state = {
        "question": "plot revenue over product",
        "session_id": "test", "datasets": [],
        "plan": "", "sql": "", "intent": "chart",
        "x_col": "product", "y_col": "revenue",
        "raw_rows": [["widget", 100]],
        "columns": ["product", "revenue"], "response": {},
    }
    result = respond_node(state)
    assert result["response"]["plotly_spec"]["layout"]["title"] == "plot revenue over product"


def test_respond_node_chart_fallback_when_no_x_y_col():
    """Falls back to column indices 0 and 1 when x_col/y_col not set."""
    state = {
        "question": "plot something",
        "session_id": "test", "datasets": [],
        "plan": "", "sql": "", "intent": "chart",
        "x_col": "", "y_col": "",
        "raw_rows": [["a", 1], ["b", 2]],
        "columns": ["label", "value"], "response": {},
    }
    result = respond_node(state)
    spec = result["response"]["plotly_spec"]
    assert spec["data"][0]["x"] == ["a", "b"]
    assert spec["data"][0]["y"] == [1, 2]


def test_full_chart_query_returns_plotly_spec(monkeypatch, mem_db_with_sales):
    """Full graph with stub LLM + in-memory DB returns a Plotly chart spec."""
    monkeypatch.setattr("src.agent.graph.get_db", make_mock_get_db(mem_db_with_sales))

    from src.integrations import llm as llm_mod

    class ChartStub:
        def complete(self, prompt, system=""):
            return json.dumps({
                "intent": "chart",
                "sql": "SELECT product, revenue FROM sales",
                "x_col": "product",
                "y_col": "revenue",
            })

    monkeypatch.setattr(llm_mod, "get_llm_client", lambda: ChartStub())

    result = analyst_graph.invoke({
        "question": "plot revenue over product",
        "session_id": "test",
        "datasets": ["sales"],
        "plan": "", "sql": "", "intent": "table",
        "x_col": "", "y_col": "",
        "raw_rows": [], "columns": [], "response": {},
    })

    r = result["response"]
    assert r["type"] == "chart"
    assert r["plotly_spec"]["data"][0]["type"] == "bar"
    assert "widget" in r["plotly_spec"]["data"][0]["x"]
    assert 100 in r["plotly_spec"]["data"][0]["y"]


def test_chart_spec_is_json_serialisable(monkeypatch, mem_db_with_sales):
    """Plotly spec must be JSON-serialisable (no numpy types)."""
    monkeypatch.setattr("src.agent.graph.get_db", make_mock_get_db(mem_db_with_sales))

    from src.integrations import llm as llm_mod

    class ChartStub:
        def complete(self, prompt, system=""):
            return json.dumps({
                "intent": "chart",
                "sql": "SELECT product, revenue FROM sales",
                "x_col": "product",
                "y_col": "revenue",
            })

    monkeypatch.setattr(llm_mod, "get_llm_client", lambda: ChartStub())

    result = analyst_graph.invoke({
        "question": "plot revenue over product",
        "session_id": "test",
        "datasets": ["sales"],
        "plan": "", "sql": "", "intent": "table",
        "x_col": "", "y_col": "",
        "raw_rows": [], "columns": [], "response": {},
    })
    # Must not raise
    json.dumps(result["response"])
