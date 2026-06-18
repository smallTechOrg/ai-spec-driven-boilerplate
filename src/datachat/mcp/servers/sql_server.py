"""Real MCP server (stdio) exposing the dataset query tools (layer 4, MCP everywhere).

Runs as its own process; opens the dataset's file-backed DuckDB read-only and serves
`inspect_schema` and `run_sql` over MCP. Both delegate to the same read-only-safe
implementations in datachat.data.query / tools.sql_tools — one source of truth.

Run standalone:  uv run python -m datachat.mcp.servers.sql_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from datachat.tools.sql_tools import (
    INSPECT_SCHEMA_DESC,
    RUN_SQL_DESC,
    tool_inspect_schema,
    tool_run_sql,
)

mcp = FastMCP("datachat-sql")


@mcp.tool(description=INSPECT_SCHEMA_DESC)
def inspect_schema(dataset_id: str) -> str:
    """List the dataset's tables, columns, and types."""
    return tool_inspect_schema(dataset_id)


@mcp.tool(description=RUN_SQL_DESC)
def run_sql(dataset_id: str, sql: str) -> str:
    """Run a single read-only SELECT against the dataset and return the rows as JSON."""
    return tool_run_sql(dataset_id, sql)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
