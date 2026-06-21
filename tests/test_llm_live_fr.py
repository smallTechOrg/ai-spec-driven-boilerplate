"""FR-001 Iteration 9 gate — real LLM integration (skipped if no API key).

These tests require ANALYST_LLM_API_KEY to be set.
"""
import json
import os
import pytest
import tempfile
from src.config import get_settings

_NEEDS_KEY = pytest.mark.skipif(
    not get_settings().llm_api_key,
    reason="no ANALYST_LLM_API_KEY — real-run tests skipped in stub mode"
)


@_NEEDS_KEY
@pytest.mark.asyncio
async def test_real_llm_query_returns_answer():
    """WHEN user sends NL question with real LLM, system SHALL return answer within 30s."""
    import time
    from src.runner import run_agent
    from httpx import AsyncClient, ASGITransport
    from src.server import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        ds_id = (await c.post("/datasets", json={"name": "live_test"})).json()["data"]["id"]
        csv_data = "product,sales\nApples,150\nBananas,200\nCherries,75\n"
        files = {"file": ("sales.csv", csv_data, "text/csv")}
        await c.post(f"/datasets/{ds_id}/files", files=files)

    start = time.time()
    from src.llm import get_model
    model = get_model()
    result = await run_agent(
        goal="What is the total sales across all products?",
        dataset_id=ds_id,
        model=model,
    )
    elapsed = time.time() - start

    assert result["status"] == "completed", result.get("answer")
    assert result["answer"], "answer should not be empty"
    assert elapsed < 30, f"took {elapsed:.1f}s — exceeds 30s limit"


@pytest.mark.asyncio
async def test_agent_surfaces_cancellation_when_large_file_not_confirmed():
    """IF user does not confirm large-file execution, agent SHALL surface cancellation message."""
    import csv
    import tempfile
    from src.runner import run_agent
    from src.graph import build_graph
    from langchain_core.messages import AIMessage, ToolMessage

    def _tc(name, args, tid):
        return {"id": tid, "name": name, "args": args, "type": "tool_call"}

    def _tool_msgs(messages):
        return [m for m in messages if isinstance(m, ToolMessage)]

    # FakeModel: get_schema → execute_sql (large file warning returned by tool) →
    # finish with cancellation message (agent reads the LARGE_FILE_WARNING and aborts)
    class _AbortModel:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            n = len(_tool_msgs(messages))
            if n == 0:
                return AIMessage(content="", tool_calls=[
                    _tc("get_dataset_schema", {"dataset_id": "ds_large"}, "t1")])
            if n == 1:
                # try to execute_sql without confirmation
                return AIMessage(content="", tool_calls=[
                    _tc("execute_sql", {"dataset_id": "ds_large", "sql": "SELECT * FROM t"}, "t2")])
            # n >= 2: execute_sql returned LARGE_FILE_WARNING — agent must cancel
            last_msg = _tool_msgs(messages)[-1]
            assert "LARGE_FILE_WARNING" in last_msg.content or "warning" in last_msg.content.lower()
            return AIMessage(content="", tool_calls=[
                _tc("finish", {
                    "answer": "Query cancelled — the dataset is larger than 100 MB. "
                              "Please confirm to proceed."
                }, "t3")])

    from src import duck
    from unittest.mock import patch, MagicMock

    fake_schema = {"tables": [{"table": "t", "columns": [{"name": "x", "type": "BIGINT"}], "sample_rows": []}]}

    with patch.object(duck, "dataset_path", return_value="/fake/large.duckdb"), \
         patch.object(duck, "dataset_schema", return_value=fake_schema), \
         patch("src.tools.os.path.getsize", return_value=110 * 1024 * 1024), \
         patch("src.tools.os.path.exists", return_value=True):
        result = await run_agent(
            goal="Show all rows",
            dataset_id="ds_large",
            model=_AbortModel(),
        )

    assert result["status"] == "completed"
    answer_lower = result["answer"].lower()
    assert "cancel" in answer_lower or "large" in answer_lower or "100" in answer_lower


@pytest.mark.asyncio
async def test_domain_prompt_instructs_ambiguous_clarification():
    """IF question is ambiguous, agent SHALL ask one clarifying question (DOMAIN_PROMPT verified)."""
    from src.runner import DOMAIN_PROMPT
    prompt_lower = DOMAIN_PROMPT.lower()
    # Rule 12 must be present: clarifying question when column not found
    assert "clarif" in prompt_lower or "which column" in prompt_lower or "ambiguous" in prompt_lower


@pytest.mark.asyncio
async def test_large_file_warning_returned_by_execute_sql_tool():
    """WHEN SQL would scan file > 100 MB, execute_sql SHALL return LARGE_FILE_WARNING."""
    from src.tools import execute_sql
    from unittest.mock import patch

    # Mock at src.tools level since that is where os is imported
    with patch("src.tools.duck.dataset_path", return_value="/fake/path.duckdb"):
        with patch("src.tools.os.path.getsize", return_value=110 * 1024 * 1024):
            with patch("src.tools.os.path.exists", return_value=True):
                result = execute_sql.invoke({
                    "dataset_id": "fake_id",
                    "sql": "SELECT * FROM t",
                    "confirmed_large": False
                })

    assert "LARGE_FILE_WARNING" in result or "warning" in result.lower()


@pytest.mark.asyncio
async def test_large_file_proceeds_with_confirmed():
    """IF user confirms, execute_sql with confirmed_large=True SHALL proceed past the warning."""
    import duckdb
    from src.tools import execute_sql
    from unittest.mock import patch
    from src import duck

    # Create a real small DuckDB file with actual data
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "fake_id.duckdb")
        con = duckdb.connect(db_path)
        con.execute("CREATE TABLE t AS SELECT 1 as x")
        con.close()

        with patch.object(duck, "dataset_path", return_value=db_path):
            with patch("src.tools.os.path.getsize", return_value=110 * 1024 * 1024):
                result = execute_sql.invoke({
                    "dataset_id": "fake_id",
                    "sql": "SELECT x FROM t",
                    "confirmed_large": True   # user confirmed
                })

    # Should get actual rows, not a warning
    assert "LARGE_FILE_WARNING" not in result
    parsed = json.loads(result)
    assert "rows" in parsed
