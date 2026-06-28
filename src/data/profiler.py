"""Auto-profiler — the `profile_dataset` tool.

Computes a dataset profile via local DuckDB queries only: row count, columns
with type + null count, and (for numeric columns) min/max/mean. No data leaves
the machine — only the summarized profile is returned. Invoked at upload time
(auto-profile) and guaranteed by the `profile` graph node before planning.
"""
from __future__ import annotations

from typing import Any

import duckdb

from data.duckdb_engine import DEFAULT_TABLE, DatasetRef, connect

# DuckDB type names that we treat as numeric for min/max/mean stats.
_NUMERIC_TYPES = {
    "TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT",
    "UTINYINT", "USMALLINT", "UINTEGER", "UBIGINT", "UHUGEINT",
    "FLOAT", "DOUBLE", "REAL", "DECIMAL",
}


def _is_numeric(duckdb_type: str) -> bool:
    base = duckdb_type.split("(")[0].strip().upper()
    return base in _NUMERIC_TYPES


def _table_columns(conn: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    rows = conn.execute(f"DESCRIBE {DEFAULT_TABLE}").fetchall()
    # DESCRIBE columns: column_name, column_type, null, key, default, extra
    return [(r[0], str(r[1])) for r in rows]


def profile_connection(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Profile the `ds` table already loaded on `conn`."""
    cols = _table_columns(conn)
    if not cols:
        raise ValueError("Dataset has no columns to profile.")

    row_count = conn.execute(f"SELECT COUNT(*) FROM {DEFAULT_TABLE}").fetchone()[0]
    row_count = int(row_count or 0)

    columns: list[dict[str, Any]] = []
    for name, dtype in cols:
        quoted = f'"{name}"'
        null_count = conn.execute(
            f"SELECT COUNT(*) FROM {DEFAULT_TABLE} WHERE {quoted} IS NULL"
        ).fetchone()[0]
        # Dataset-wide distinct count — used by the privacy gate to decide whether
        # a categorical column is a low-cardinality grouping label (its values may
        # cross to the LLM as labels) or a high-cardinality row-level secret
        # (values never cross). This is a derived NUMBER; raw values never leave.
        distinct_count = conn.execute(
            f"SELECT COUNT(DISTINCT {quoted}) FROM {DEFAULT_TABLE}"
        ).fetchone()[0]
        col: dict[str, Any] = {
            "name": name,
            "type": dtype,
            "null_count": int(null_count or 0),
            "distinct_count": int(distinct_count or 0),
        }
        if _is_numeric(dtype) and row_count > 0:
            stats = conn.execute(
                f"SELECT MIN({quoted}), MAX({quoted}), AVG({quoted}) "
                f"FROM {DEFAULT_TABLE}"
            ).fetchone()
            mn, mx, mean = stats
            col["min"] = _num(mn)
            col["max"] = _num(mx)
            col["mean"] = _num(mean)
        columns.append(col)

    return {"row_count": row_count, "columns": columns}


def profile_dataset(ref: DatasetRef) -> dict[str, Any]:
    """Open the dataset locally and compute its profile."""
    conn = connect(ref)
    try:
        return profile_connection(conn)
    finally:
        conn.close()


def schema_from_profile(profile: dict[str, Any]) -> list[dict[str, str]]:
    """Reduce a profile to the column metadata (name/type) given to the LLM."""
    return [
        {"name": c["name"], "type": c["type"]}
        for c in profile.get("columns", [])
    ]


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None
