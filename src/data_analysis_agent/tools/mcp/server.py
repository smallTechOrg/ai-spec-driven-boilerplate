from __future__ import annotations

from pathlib import Path

import duckdb
from mcp.server.fastmcp import FastMCP

DEFAULT_MAX_ROWS = 200


class RecoverableQueryError(ValueError):
    """A query problem the LLM can fix by retrying.

    FastMCP turns any exception raised inside a tool into a ``CallToolResult`` with
    ``isError=True``, so raising this is how a recoverable error (bad SQL, non-SELECT)
    is surfaced to the agent for self-correction.
    """


def build_server(
    source: dict, capability_description: str, max_rows: int = DEFAULT_MAX_ROWS
) -> FastMCP:
    """Build an in-process MCP server that wraps ONE Parquet file via DuckDB.

    The server exposes a single read-only ``run_query`` tool. The Parquet is
    registered as a DuckDB view named ``source['table_name']`` so the SQL the LLM
    writes matches the table name advertised in the planning prompt.

    Args:
        source: Serialised data-source dict with ``table_name`` and ``parquet_path``.
        capability_description: Description shown to the LLM for the ``run_query`` tool.
        max_rows: Maximum number of result rows returned per query.

    Returns:
        A configured :class:`FastMCP` server (not yet connected to a client). The
        backing DuckDB connection is attached as ``server._duckdb_conn`` so the
        caller can close it when the run ends.

    Raises:
        FileNotFoundError: If the source has no readable Parquet file (fatal — the
            agent cannot answer without data).
    """
    table = source["table_name"]
    conn = _open_view(source.get("parquet_path"), table)

    server = FastMCP(f"csv::{table}")

    def run_query(query: str) -> str:
        """Run a read-only SQL SELECT against this dataset and return CSV rows."""
        return _run_select(conn, query, max_rows)

    server.add_tool(run_query, name="run_query", description=capability_description)
    server._duckdb_conn = conn  # type: ignore[attr-defined]
    return server


def _open_view(parquet_path: str | None, table: str) -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB connection with the Parquet registered as a view."""
    if not parquet_path or not Path(parquet_path).exists():
        raise FileNotFoundError(
            f"Parquet file not found for table {table!r}: {parquet_path!r}"
        )
    conn = duckdb.connect(database=":memory:")
    safe_path = parquet_path.replace("'", "''")
    safe_table = table.replace('"', '""')
    # DuckDB DDL cannot take bind parameters; the path is server-generated and escaped.
    conn.execute(f'CREATE VIEW "{safe_table}" AS SELECT * FROM read_parquet(\'{safe_path}\')')
    return conn


def _run_select(conn: duckdb.DuckDBPyConnection, query: str, max_rows: int) -> str:
    """Validate and run a SELECT, returning a compact CSV string (``max_rows`` cap)."""
    if not query.strip().upper().startswith("SELECT"):
        raise RecoverableQueryError(f"Only SELECT statements are allowed. Got: {query[:80]}")
    try:
        cursor = conn.execute(query)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(max_rows)
    except duckdb.Error as exc:
        raise RecoverableQueryError(str(exc))
    lines = [",".join(columns)]
    lines += [",".join("" if v is None else str(v) for v in row) for row in rows]
    return "\n".join(lines)


# --- Dataset (multi-table) server -------------------------------------------
# A dataset's connector opens ONE DuckDB connection with all of the dataset's tables as views,
# then calls build_dataset_server to expose one `query_{table}` capability per table. All tables
# share the connection, so any capability's SQL may JOIN the dataset's other tables.

def new_connection() -> duckdb.DuckDBPyConnection:
    """Return a fresh in-memory DuckDB connection (the caller registers views / ATTACHes)."""
    return duckdb.connect(database=":memory:")


def register_parquet_view(conn: duckdb.DuckDBPyConnection, table_name: str, parquet_path: str | None) -> None:
    """Register a Parquet file as a read-only view named ``table_name`` on ``conn``."""
    if not parquet_path or not Path(parquet_path).exists():
        raise FileNotFoundError(f"Parquet file not found for table {table_name!r}: {parquet_path!r}")
    safe_path = parquet_path.replace("'", "''")
    safe_table = table_name.replace('"', '""')
    conn.execute(f'CREATE VIEW "{safe_table}" AS SELECT * FROM read_parquet(\'{safe_path}\')')


def build_dataset_server(
    dataset_name: str,
    conn: duckdb.DuckDBPyConnection,
    tables: list[dict],
    max_rows: int = DEFAULT_MAX_ROWS,
) -> FastMCP:
    """Build one MCP server for a dataset: a ``query_{table}`` tool per table over ``conn``.

    Args:
        dataset_name: The dataset (tool) canonical name — used as the server label.
        conn: A DuckDB connection where every table is already a view (parquet views or ATTACH).
        tables: Dicts with ``table_name`` and optional ``capability_description``.
        max_rows: Row cap per query.

    Returns:
        A :class:`FastMCP` server with the connection attached as ``server._duckdb_conn``.
    """
    server = FastMCP(f"dataset::{dataset_name}")
    for table in tables:
        table_name = table["table_name"]
        description = table.get("capability_description") or _default_capability_description(table_name, tables)
        server.add_tool(_make_table_query(conn, max_rows), name=f"query_{table_name}", description=description)
    server._duckdb_conn = conn  # type: ignore[attr-defined]
    return server


def _make_table_query(conn: duckdb.DuckDBPyConnection, max_rows: int):
    """Return a ``query(query: str) -> str`` tool fn bound to a dataset's DuckDB connection."""
    def query(query: str) -> str:
        """Run a read-only SQL SELECT against this dataset and return CSV rows."""
        return _run_select(conn, query, max_rows)
    return query


def _default_capability_description(table_name: str, tables: list[dict]) -> str:
    """Fallback capability description naming the table and its joinable siblings."""
    siblings = [t["table_name"] for t in tables if t["table_name"] != table_name]
    note = f" You may JOIN sibling tables in this dataset: {', '.join(siblings)}." if siblings else ""
    return f"Run a read-only SQL SELECT; primary table is '{table_name}'.{note}"
