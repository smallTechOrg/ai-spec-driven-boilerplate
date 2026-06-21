"""FR-001 analyst workflow criteria.

Gate command: uv run --extra dev pytest tests/test_analyst_fr.py -v
"""
import csv as csv_mod
import json
import os
import tempfile

import pytest
import pytest_asyncio
from langchain_core.messages import AIMessage, ToolMessage

from src.runner import DOMAIN_PROMPT, run_agent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tc(name: str, args: dict, tid: str):
    return {"id": tid, "name": name, "args": args, "type": "tool_call"}


def _tool_msgs(messages) -> list[ToolMessage]:
    return [m for m in messages if isinstance(m, ToolMessage)]


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def seeded_analyst_dataset():
    """Real CSV → DuckDB for analyst workflow gate tests."""
    from src.domain import Dataset, DataTable
    from src.db import get_sessionmaker
    from src import duck

    ds = Dataset(name="analyst_gate_orders")
    async with get_sessionmaker()() as s:
        s.add(ds)
        await s.commit()
        ds_id = ds.id

    rows = [
        ["customer", "order_total", "status"],
        ["Alice", 250, "completed"],
        ["Bob", 80, "pending"],
        ["Carol", 430, "completed"],
        ["Dave", 120, "cancelled"],
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", newline="") as f:
        csv_mod.writer(f).writerows(rows)
        tmp = f.name

    import asyncio
    try:
        meta = await asyncio.to_thread(duck.ingest_file, ds_id, "orders.csv", tmp, "orders.csv")
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
# FR criterion 1: DOMAIN_PROMPT instructs follow-up questions
# ---------------------------------------------------------------------------

def test_domain_prompt_instructs_follow_up_questions():
    """The DOMAIN_PROMPT SHALL instruct agent to append follow-up questions."""
    assert "follow-up" in DOMAIN_PROMPT.lower() or "What to explore next" in DOMAIN_PROMPT, (
        "DOMAIN_PROMPT must contain follow-up question instruction so the real LLM appends suggestions")


# ---------------------------------------------------------------------------
# FR criterion 2: follow-up questions reference a column name
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_follow_up_questions_reference_column_name(seeded_analyst_dataset):
    """WHEN agent produces result, answer SHALL contain follow-up referencing a column name.

    The FakeModel's finish answer explicitly includes the '---' separator block and a
    follow-up question that references the 'order_total' column — the structural
    constraint the DOMAIN_PROMPT mandates. We assert both the separator and a column
    reference appear in the returned answer.
    """
    ds_id, table = seeded_analyst_dataset

    class _FollowUpModel:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            n = len(_tool_msgs(messages))
            if n == 0:
                return AIMessage(content="", tool_calls=[
                    _tc("execute_sql", {
                        "dataset_id": ds_id,
                        "sql": f"SELECT customer, order_total FROM {table} ORDER BY order_total DESC",
                    }, "f1")])
            data = {}
            tms = _tool_msgs(messages)
            try:
                data = json.loads(tms[-1].content)
            except Exception:
                pass
            rows = data.get("rows", [])
            cols = data.get("columns", ["customer", "order_total"])
            header = "| " + " | ".join(cols) + " |"
            sep = "| " + " | ".join("---" for _ in cols) + " |"
            body_lines = ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
            md_table = "\n".join([header, sep] + body_lines)
            answer = (
                f"Here are the orders ranked by order_total:\n\n{md_table}\n\n"
                "---\n"
                "**What to explore next:**\n"
                "- Which customers have an order_total above the average?\n"
                "- How does the order_total distribution look by status?\n"
            )
            return AIMessage(content="", tool_calls=[
                _tc("finish", {"answer": answer}, "f2")])

    result = await run_agent(
        goal="Rank customers by order total",
        dataset_id=ds_id,
        model=_FollowUpModel(),
    )

    assert result["status"] == "completed"
    answer = result["answer"]

    assert "---" in answer, (
        f"Answer must contain '---' separator before follow-up block. Got: {answer!r}")
    assert "order_total" in answer, (
        f"Answer must reference the 'order_total' column in follow-up questions. Got: {answer!r}")
    assert "?" in answer, (
        f"Answer must contain at least one follow-up question (ends with '?'). Got: {answer!r}")


# ---------------------------------------------------------------------------
# FR criterion 3: DOMAIN_PROMPT instructs plain English explain
# ---------------------------------------------------------------------------

def test_domain_prompt_instructs_plain_english_explain():
    """The DOMAIN_PROMPT SHALL instruct agent to explain in plain English without raw SQL."""
    assert "plain" in DOMAIN_PROMPT.lower() or "explain" in DOMAIN_PROMPT.lower(), (
        "DOMAIN_PROMPT must contain plain-English explain instruction so the real LLM "
        "responds without exposing raw SQL when the user says 'explain'")
