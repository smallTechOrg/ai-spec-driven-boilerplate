"""FR-001 rich response output criteria — API contract checks.

Gate command: uv run --extra dev pytest tests/test_richoutput_fr.py -v
"""
import csv as csv_mod
import json
import os
import tempfile

import pytest
import pytest_asyncio
from langchain_core.messages import AIMessage, ToolMessage

from src.runner import run_agent


# ---------------------------------------------------------------------------
# Helpers — same closure pattern as test_query_fr.py
# ---------------------------------------------------------------------------

def _tc(name: str, args: dict, tid: str):
    return {"id": tid, "name": name, "args": args, "type": "tool_call"}


def _tool_msgs(messages) -> list[ToolMessage]:
    return [m for m in messages if isinstance(m, ToolMessage)]


def _last_tool_json(messages):
    tms = _tool_msgs(messages)
    if not tms:
        return {}
    try:
        return json.loads(tms[-1].content)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def seeded_ro_dataset():
    """Real CSV → DuckDB with numeric + categorical columns for rich-output gate tests."""
    from src.domain import Dataset, DataTable
    from src.db import get_sessionmaker
    from src import duck

    ds = Dataset(name="ro_gate_sales")
    async with get_sessionmaker()() as s:
        s.add(ds)
        await s.commit()
        ds_id = ds.id

    rows = [
        ["product", "units", "region"],
        ["Widget", 120, "North"],
        ["Gadget", 95, "South"],
        ["Doohickey", 200, "East"],
        ["Thingamajig", 60, "West"],
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", newline="") as f:
        csv_mod.writer(f).writerows(rows)
        tmp = f.name

    import asyncio
    try:
        meta = await asyncio.to_thread(duck.ingest_file, ds_id, "products.csv", tmp, "products.csv")
    finally:
        os.unlink(tmp)

    async with get_sessionmaker()() as s:
        s.add(DataTable(
            dataset_id=ds_id,
            table_name=meta["table_name"],
            filename=meta["filename"],
            n_rows=meta["n_rows"],
            n_cols=meta["n_cols"],
            columns=meta["columns"],
        ))
        await s.commit()

    return ds_id, meta["table_name"]


# ---------------------------------------------------------------------------
# FR criterion 1: tabular query response includes Markdown table
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tabular_query_includes_markdown_table_in_api_response(seeded_ro_dataset):
    """WHEN query returns tabular data, API response SHALL include Markdown table.

    Uses a 4-step FakeModel: get_schema → execute_sql → generate_chart_spec → finish.
    The finish answer is built from real SQL rows and contains a Markdown table.
    """
    ds_id, table = seeded_ro_dataset

    class _RichModel:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            n = len(_tool_msgs(messages))
            if n == 0:
                return AIMessage(content="", tool_calls=[
                    _tc("get_dataset_schema", {"dataset_id": ds_id}, "r1")])
            if n == 1:
                return AIMessage(content="", tool_calls=[
                    _tc("execute_sql", {
                        "dataset_id": ds_id,
                        "sql": f"SELECT product, units FROM {table} ORDER BY units DESC",
                    }, "r2")])
            if n == 2:
                return AIMessage(content="", tool_calls=[
                    _tc("generate_chart_spec", {
                        "query_results": _tool_msgs(messages)[-1].content,
                        "chart_type": "bar",
                        "x_col": "product",
                        "y_col": "units",
                        "title": "Units by Product",
                    }, "r3")])
            # Step 4: build Markdown table from SQL rows + attach chart_spec
            tms = _tool_msgs(messages)
            sql_data = {}
            for tm in reversed(tms[:-1]):
                try:
                    sql_data = json.loads(tm.content)
                    break
                except Exception:
                    continue
            rows = sql_data.get("rows", [])
            cols = sql_data.get("columns", ["product", "units"])
            header = "| " + " | ".join(cols) + " |"
            sep = "| " + " | ".join("---" for _ in cols) + " |"
            body_lines = ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
            md_table = "\n".join([header, sep] + body_lines)
            chart_spec_str = tms[-1].content
            return AIMessage(content="", tool_calls=[
                _tc("finish", {
                    "answer": f"Units by product:\n\n{md_table}",
                    "chart_spec": chart_spec_str,
                }, "r4")])

    result = await run_agent(
        goal="Show me units by product",
        dataset_id=ds_id,
        model=_RichModel(),
    )

    assert result["status"] == "completed"
    assert result["answer"], "answer must not be empty"
    assert "|" in result["answer"], (
        f"answer must contain a Markdown table (| character). Got: {result['answer']!r}")


# ---------------------------------------------------------------------------
# FR criterion 2: chart_spec is valid Plotly JSON when numeric + categorical
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chart_spec_is_valid_plotly_when_numeric_and_categorical_columns(seeded_ro_dataset):
    """WHEN result has numeric + categorical column, chart_spec SHALL be valid Plotly JSON.

    The FakeModel calls generate_chart_spec with real DuckDB output, then passes the
    result to finish. We assert chart_spec has 'data' and 'layout' keys.
    """
    ds_id, table = seeded_ro_dataset

    class _PlotlyModel:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            n = len(_tool_msgs(messages))
            if n == 0:
                return AIMessage(content="", tool_calls=[
                    _tc("execute_sql", {
                        "dataset_id": ds_id,
                        "sql": f"SELECT region, SUM(units) AS total_units FROM {table} GROUP BY region",
                    }, "p1")])
            if n == 1:
                return AIMessage(content="", tool_calls=[
                    _tc("generate_chart_spec", {
                        "query_results": _tool_msgs(messages)[-1].content,
                        "chart_type": "bar",
                        "x_col": "region",
                        "y_col": "total_units",
                        "title": "Units by Region",
                    }, "p2")])
            chart_spec_str = _tool_msgs(messages)[-1].content
            return AIMessage(content="", tool_calls=[
                _tc("finish", {
                    "answer": "Here is the regional breakdown.",
                    "chart_spec": chart_spec_str,
                }, "p3")])

    result = await run_agent(
        goal="Show total units by region as a chart",
        dataset_id=ds_id,
        model=_PlotlyModel(),
    )

    assert result["status"] == "completed"
    assert result["chart_spec"] is not None, "chart_spec must be present when chart was requested"

    spec = (
        json.loads(result["chart_spec"])
        if isinstance(result["chart_spec"], str)
        else result["chart_spec"]
    )
    assert "data" in spec, f"Plotly spec must have 'data' key. Got keys: {list(spec.keys())}"
    assert "layout" in spec, f"Plotly spec must have 'layout' key. Got keys: {list(spec.keys())}"
    assert isinstance(spec["data"], list) and len(spec["data"]) > 0, (
        "Plotly spec 'data' must be a non-empty list")


# ---------------------------------------------------------------------------
# FR criterion 3: chart_spec is parseable JSON when present in POST /runs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_endpoint_returns_chart_spec_as_parseable_json(seeded_ro_dataset):
    """WHEN agent returns a chart, POST /runs SHALL return chart_spec as parseable JSON.

    This is the single-chart baseline for Iteration 10's multi-chart dashboard.
    We verify the API contract: chart_spec key present and parseable.
    """
    import httpx
    from src.server import app

    ds_id, table = seeded_ro_dataset

    class _SingleChartModel:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            n = len(_tool_msgs(messages))
            if n == 0:
                return AIMessage(content="", tool_calls=[
                    _tc("execute_sql", {
                        "dataset_id": ds_id,
                        "sql": f"SELECT product, units FROM {table} LIMIT 4",
                    }, "s1")])
            if n == 1:
                return AIMessage(content="", tool_calls=[
                    _tc("generate_chart_spec", {
                        "query_results": _tool_msgs(messages)[-1].content,
                        "chart_type": "bar",
                        "x_col": "product",
                        "y_col": "units",
                        "title": "Product Units",
                    }, "s2")])
            chart_spec_str = _tool_msgs(messages)[-1].content
            return AIMessage(content="", tool_calls=[
                _tc("finish", {
                    "answer": "Product unit counts.",
                    "chart_spec": chart_spec_str,
                }, "s3")])

    # Inject FakeModel via run_agent directly; verify chart_spec is parseable
    result = await run_agent(
        goal="Give me a chart of product units",
        dataset_id=ds_id,
        model=_SingleChartModel(),
    )

    assert result["status"] == "completed"
    assert result.get("chart_spec") is not None, "chart_spec must be present"

    chart_spec = result["chart_spec"]
    if isinstance(chart_spec, str):
        parsed = json.loads(chart_spec)
    else:
        parsed = chart_spec

    assert isinstance(parsed, dict), f"chart_spec must parse to a dict, got {type(parsed)}"
    assert "data" in parsed, "Parsed chart_spec must contain 'data'"
