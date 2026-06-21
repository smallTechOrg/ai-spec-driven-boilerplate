"""FR-001 token economy criteria.

Gate command: uv run --extra dev pytest tests/test_tokens_fr.py -v
"""
import csv as csv_mod
import json
import os
import tempfile

import pytest
import pytest_asyncio
import httpx
from langchain_core.messages import AIMessage, ToolMessage

from src.runner import run_agent, DOMAIN_PROMPT
from src.server import app


# ---------------------------------------------------------------------------
# Helpers (inline — same pattern as test_query_fr.py)
# ---------------------------------------------------------------------------

def _tc(name: str, args: dict, tid: str):
    return {"id": tid, "name": name, "args": args, "type": "tool_call"}


def _tool_msgs(messages) -> list[ToolMessage]:
    return [m for m in messages if isinstance(m, ToolMessage)]


# ---------------------------------------------------------------------------
# Shared fixture: CSV dataset seeded into DuckDB
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def seeded_token_dataset():
    """Real CSV → DuckDB with simple numeric + categorical columns."""
    from src.domain import Dataset, DataTable
    from src.db import get_sessionmaker
    from src import duck

    ds = Dataset(name="token_test_sales")
    async with get_sessionmaker()() as s:
        s.add(ds)
        await s.commit()
        ds_id = ds.id

    rows = [
        ["product", "units"],
        ["Widget", 100],
        ["Gadget", 200],
        ["Doohickey", 50],
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", newline="") as f:
        csv_mod.writer(f).writerows(rows)
        tmp = f.name

    import asyncio
    try:
        meta = await asyncio.to_thread(duck.ingest_file, ds_id, "sales.csv", tmp, "sales.csv")
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
# Test 1: DOMAIN_PROMPT sends schema only — no raw row reading
# ---------------------------------------------------------------------------

def test_domain_prompt_instructs_schema_only_no_raw_rows():
    """The system SHALL send only dataset schema (not raw rows) to the LLM."""
    prompt_lower = DOMAIN_PROMPT.lower()
    # Must reference schema inspection — either 'schema' keyword or get_dataset_schema tool
    assert "schema" in prompt_lower or "get_dataset_schema" in DOMAIN_PROMPT, (
        "DOMAIN_PROMPT must instruct the LLM to inspect schema before querying"
    )
    # Must NOT instruct the LLM to use read_csv (which would load raw rows)
    assert "read_csv" not in DOMAIN_PROMPT, (
        "DOMAIN_PROMPT must not instruct the LLM to use read_csv (raw data loading)"
    )


# ---------------------------------------------------------------------------
# Test 2: audit log has prompt_tokens and completion_tokens per SQL execution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_has_token_counts(seeded_token_dataset):
    """The system SHALL log prompt_tokens and completion_tokens per SQL execution.

    FakeModel steps:
      Step 1: get_dataset_schema
      Step 2: execute_sql
      Step 3: finish
    Token values are 0 in stub mode — the test asserts field presence and int type.
    """
    ds_id, table = seeded_token_dataset
    thread_id = "token-audit-test-001"

    class _AuditTokenModel:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            n = len(_tool_msgs(messages))
            if n == 0:
                return AIMessage(content="", tool_calls=[
                    _tc("get_dataset_schema", {"dataset_id": ds_id}, "t1")])
            if n == 1:
                return AIMessage(content="", tool_calls=[
                    _tc("execute_sql", {
                        "dataset_id": ds_id,
                        "sql": f"SELECT product, units FROM {table} ORDER BY units DESC",
                    }, "t2")])
            # Step 3: finish
            return AIMessage(content="", tool_calls=[
                _tc("finish", {"answer": "| product | units |\n|---|---|\n| Gadget | 200 |"}, "t3")])

    await run_agent(
        goal="Show me all products by units",
        dataset_id=ds_id,
        thread_id=thread_id,
        model=_AuditTokenModel(),
    )

    # Check the audit log via the server endpoint
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/sessions/{thread_id}/audit")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    body = resp.json()
    assert body["ok"] is True, f"Expected ok=true, got: {body}"
    entries = body["data"]
    assert len(entries) >= 1, (
        f"Expected at least 1 audit log entry for session {thread_id}, got {len(entries)}"
    )

    for entry in entries:
        assert "prompt_tokens" in entry, (
            f"audit entry missing 'prompt_tokens' key. Keys present: {list(entry.keys())}"
        )
        assert "completion_tokens" in entry, (
            f"audit entry missing 'completion_tokens' key. Keys present: {list(entry.keys())}"
        )
        assert isinstance(entry["prompt_tokens"], int), (
            f"prompt_tokens must be int, got {type(entry['prompt_tokens']).__name__}: {entry['prompt_tokens']!r}"
        )
        assert isinstance(entry["completion_tokens"], int), (
            f"completion_tokens must be int, got {type(entry['completion_tokens']).__name__}: {entry['completion_tokens']!r}"
        )


# ---------------------------------------------------------------------------
# Test 3: GET /sessions/{id} returns cumulative token totals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_endpoint_returns_cumulative_token_totals(seeded_token_dataset):
    """GET /sessions/{id} SHALL include running total_input_tokens and total_output_tokens.

    Runs the agent twice on the same thread_id, then asserts the session endpoint
    returns non-negative integer totals. FakeModel returns 0 tokens — values will be 0
    but fields must exist as integers.
    """
    ds_id, table = seeded_token_dataset
    thread_id = "token-totals-test-001"

    class _TotalsModel:
        def __init__(self):
            self._call = 0

        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            n = len(_tool_msgs(messages))
            if n == 0:
                return AIMessage(content="", tool_calls=[
                    _tc("execute_sql", {
                        "dataset_id": ds_id,
                        "sql": f"SELECT product, units FROM {table} LIMIT 2",
                    }, f"t{self._call}_1")])
            return AIMessage(content="", tool_calls=[
                _tc("finish", {
                    "answer": "| product | units |\n|---|---|\n| Widget | 100 |"
                }, f"t{self._call}_2")])

    # Run 1
    model1 = _TotalsModel()
    model1._call = 1
    await run_agent(
        goal="Show me top 2 products",
        dataset_id=ds_id,
        thread_id=thread_id,
        model=model1,
    )

    # Run 2
    model2 = _TotalsModel()
    model2._call = 2
    await run_agent(
        goal="Show me top 2 products again",
        dataset_id=ds_id,
        thread_id=thread_id,
        model=model2,
    )

    # Check the session endpoint
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/sessions/{thread_id}")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    body = resp.json()
    assert body["ok"] is True, f"Expected ok=true, got: {body}"
    data = body["data"]

    assert "total_input_tokens" in data, (
        f"GET /sessions/{{id}} missing 'total_input_tokens'. Keys: {list(data.keys())}"
    )
    assert "total_output_tokens" in data, (
        f"GET /sessions/{{id}} missing 'total_output_tokens'. Keys: {list(data.keys())}"
    )
    assert isinstance(data["total_input_tokens"], int), (
        f"total_input_tokens must be int, got {type(data['total_input_tokens']).__name__}"
    )
    assert isinstance(data["total_output_tokens"], int), (
        f"total_output_tokens must be int, got {type(data['total_output_tokens']).__name__}"
    )
    assert data["total_input_tokens"] >= 0, (
        f"total_input_tokens must be non-negative, got {data['total_input_tokens']}"
    )
    assert data["total_output_tokens"] >= 0, (
        f"total_output_tokens must be non-negative, got {data['total_output_tokens']}"
    )

    # Verify run_count accumulated across 2 runs
    assert data.get("run_count", 0) >= 2, (
        f"run_count should be >= 2 after two runs, got {data.get('run_count')}"
    )
