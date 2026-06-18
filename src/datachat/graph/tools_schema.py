"""Tool schemas bound to Gemini for the plan_action call.

The LLM chooses among inspect_schema / run_sql / finish. `dataset_id` is NOT exposed to
the model — it is injected from AgentState at execution time. These schemas mirror the
real MCP server tools (mcp/servers/sql_server.py); execution delegates to the same
read-only-safe implementations.
"""

from __future__ import annotations

from langchain_core.tools import tool

from datachat.tools.sql_tools import INSPECT_SCHEMA_DESC, RUN_SQL_DESC


@tool(description=INSPECT_SCHEMA_DESC)
def inspect_schema() -> str:
    """List the dataset's tables, columns, and types."""  # executed via state injection
    return ""


@tool(description=RUN_SQL_DESC)
def run_sql(sql: str) -> str:
    """Run a single read-only SELECT against the dataset (DuckDB)."""
    return ""


@tool(description="Finish: return the final plain-English answer plus the supporting result table.")
def finish(
    answer: str,
    result_columns: list[str] | None = None,
    result_rows: list[list] | None = None,
) -> str:
    """Call when you have the answer. Pass the columns/rows from your last run_sql."""
    return ""


TOOLS = [inspect_schema, run_sql, finish]
