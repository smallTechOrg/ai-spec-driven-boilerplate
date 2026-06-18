"""Tool registry — typed, pure functions exposed to the agent (layer 4).

These are the canonical implementations. They are exposed two ways over one protocol:
- as a real MCP server (mcp/servers/sql_server.py, stdio) for any MCP client, and
- bound to Gemini as LangChain tools in the graph (graph/nodes.py),
both delegating here so there is a single source of truth. Errors are returned as values
(strings), never raised, so the ReAct loop can observe and self-correct.
"""

from __future__ import annotations

import json

from datachat.data.query import QueryError, inspect_schema, run_sql

INSPECT_SCHEMA_DESC = (
    "List the dataset's tables with their columns and types. Call this first to learn "
    "the exact table and column names before writing SQL."
)

RUN_SQL_DESC = (
    "Run a single read-only SQL SELECT (DuckDB dialect) against the dataset's tables and "
    "return the result rows. Only SELECT / WITH...SELECT is allowed; writes are rejected. "
    "Use exact table names from inspect_schema."
)


def tool_inspect_schema(dataset_id: str) -> str:
    try:
        return json.dumps(inspect_schema(dataset_id), default=str)
    except QueryError as exc:
        return f"ERROR: {exc}"


def tool_run_sql(dataset_id: str, sql: str) -> str:
    try:
        result = run_sql(dataset_id, sql)
    except QueryError as exc:
        return f"ERROR: {exc}"
    return json.dumps(result, default=str)
