"""Local, read-only DuckDB query engine over the user's data files.

The raw rows live ONLY here (in-process DuckDB over the on-disk source file).
This module is the local execution boundary: it runs the generated SQL against
the dataset's table and returns rows + column metadata. Those raw rows stay
local — no code in this module sends anything to an LLM.

Phase 1 loads the dataset's table per request from the stored source file
(`DatasetRef.source_path`). Phase 2 will persist DuckDB tables on disk.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import duckdb

# Default in-graph table name a generated query references. The plan prompt is
# told the table is named `ds`, so the SQL the LLM drafts uses `ds`.
DEFAULT_TABLE = "ds"

# Statement prefixes that are allowed (read-only). Anything else is rejected so
# the local store is never mutated and no DDL/DML can run.
_SELECT_RE = re.compile(r"^\s*(?:with\b|select\b)", re.IGNORECASE)
# Reject obviously destructive / multi-statement attempts even if they begin
# with SELECT (e.g. "SELECT 1; DROP TABLE ds").
_FORBIDDEN_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|copy|truncate|"
    r"replace|pragma|install|load|export|import)\b",
    re.IGNORECASE,
)


class QueryError(Exception):
    """Raised when a query is rejected or fails to execute locally."""


@dataclass
class DatasetRef:
    """Just enough metadata to (re)load a dataset's rows into DuckDB."""

    dataset_id: str
    source_path: str
    source_kind: str            # "csv" | "excel"
    duckdb_table: str           # logical table name (registered as DEFAULT_TABLE)
    sheet_name: str | None = None


def _is_read_only(sql: str) -> bool:
    if not sql or not _SELECT_RE.match(sql):
        return False
    # Strip a single trailing semicolon, then forbid further statements.
    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        return False
    if _FORBIDDEN_RE.search(stripped):
        return False
    return True


def _sql_str(path: str) -> str:
    """Single-quote a local file path for inlining into DuckDB SQL.

    DuckDB does not accept bound parameters inside read_csv_auto/read_parquet in
    a CREATE VIEW, so the (server-controlled) path is inlined with quote-escaping.
    """
    return "'" + str(path).replace("'", "''") + "'"


def _load_table(conn: duckdb.DuckDBPyConnection, ref: DatasetRef) -> None:
    """Register the dataset's rows as a view named DEFAULT_TABLE."""
    if ref.source_kind == "csv":
        conn.execute(
            f"CREATE OR REPLACE VIEW {DEFAULT_TABLE} AS "
            f"SELECT * FROM read_csv_auto({_sql_str(ref.source_path)}, header=true)"
        )
    elif ref.source_kind == "excel":
        # Excel sheets were materialised to a per-sheet parquet cache at ingest
        # time; we read that cached local file back.
        conn.execute(
            f"CREATE OR REPLACE VIEW {DEFAULT_TABLE} AS "
            f"SELECT * FROM read_parquet({_sql_str(ref.source_path)})"
        )
    else:
        raise QueryError(f"Unsupported source kind: {ref.source_kind!r}")


def connect(ref: DatasetRef) -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB connection with the dataset loaded as `ds`."""
    conn = duckdb.connect(database=":memory:")
    _load_table(conn, ref)
    return conn


def run_query(conn: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[dict], list[dict]]:
    """Run a read-only SELECT and return (rows, columns).

    rows: list[dict] keyed by column name. columns: [{name, type}, ...].
    Rejects any non-SELECT / multi-statement / DDL-DML SQL.
    """
    if not _is_read_only(sql):
        raise QueryError(
            "Only read-only SELECT statements are permitted; "
            "the generated SQL was rejected."
        )
    try:
        cursor = conn.execute(sql)
    except Exception as exc:  # bad SQL, type error, unknown column, etc.
        raise QueryError(str(exc)) from exc

    col_names = [d[0] for d in cursor.description] if cursor.description else []
    col_types = [str(d[1]) for d in cursor.description] if cursor.description else []
    columns = [{"name": n, "type": t} for n, t in zip(col_names, col_types)]
    raw = cursor.fetchall()
    rows = [dict(zip(col_names, _coerce_row(r))) for r in raw]
    return rows, columns


def duckdb_query(sql: str, ref: DatasetRef) -> tuple[list[dict], list[dict]]:
    """Convenience: open a connection, run the query, close it."""
    conn = connect(ref)
    try:
        return run_query(conn, sql)
    finally:
        conn.close()


def _coerce_row(row: tuple) -> list[Any]:
    """Make DuckDB values JSON-serialisable (Decimal, date, etc.)."""
    out: list[Any] = []
    for v in row:
        if v is None or isinstance(v, (str, int, float, bool)):
            out.append(v)
        else:
            # Decimals, dates, timestamps -> string/float for transport.
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                out.append(str(v))
    return out
