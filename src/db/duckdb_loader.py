"""
DuckDB-based dataset loader.

Reads uploaded CSV/Excel/JSON files, infers schema (column names + DuckDB types),
and returns column info + row count — without loading raw data into memory beyond
what DuckDB needs for schema inference.

Never includes raw rows in return values. Schema only.
"""
import re
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


def _safe_view_name(filename: str) -> str:
    """
    Derive a safe SQL view name from a filename.

    Lowercases the stem, replaces spaces with underscores, strips non-alphanumeric
    characters (except underscores), and prefixes 't_' if the result starts with a digit.
    """
    stem = Path(filename).stem
    name = stem.lower().replace(" ", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    if not name:
        name = "dataset"
    if name[0].isdigit():
        name = "t_" + name
    return name


def _load_excel_as_df(file_path: str) -> pd.DataFrame:
    """Load the first sheet of an Excel file into a pandas DataFrame."""
    import openpyxl

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return pd.DataFrame()

    headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
    data = [dict(zip(headers, row)) for row in rows[1:]]
    return pd.DataFrame(data, columns=headers)


def load_dataset_schema(file_path: str, file_type: str) -> dict[str, Any]:
    """
    Open the file with DuckDB, infer columns and row count.

    Returns:
        {
            "columns": [{"name": str, "type": str}, ...],
            "row_count": int,
            "view_name": str,  # filename without extension, safe for SQL
        }

    Raises:
        ValueError: if file_type is unsupported
        RuntimeError: if DuckDB fails to parse the file
    """
    supported = {"csv", "xlsx", "json"}
    if file_type not in supported:
        raise ValueError(
            f"Unsupported file_type {file_type!r}. Must be one of: {supported}"
        )

    view_name = _safe_view_name(Path(file_path).name)
    conn = duckdb.connect(":memory:")

    try:
        if file_type == "csv":
            describe_sql = (
                f"DESCRIBE SELECT * FROM read_csv_auto('{file_path}') LIMIT 0"
            )
            count_sql = f"SELECT COUNT(*) FROM read_csv_auto('{file_path}')"
        elif file_type == "json":
            describe_sql = (
                f"DESCRIBE SELECT * FROM read_json_auto('{file_path}') LIMIT 0"
            )
            count_sql = f"SELECT COUNT(*) FROM read_json_auto('{file_path}')"
        elif file_type == "xlsx":
            df = _load_excel_as_df(file_path)
            conn.register("_temp_excel", df)
            describe_sql = "DESCRIBE SELECT * FROM _temp_excel LIMIT 0"
            count_sql = "SELECT COUNT(*) FROM _temp_excel"

        try:
            described = conn.execute(describe_sql).fetchall()
            row_count_result = conn.execute(count_sql).fetchone()
        except Exception as exc:
            raise RuntimeError(
                f"DuckDB failed to parse {file_path!r} as {file_type}: {exc}"
            ) from exc

        # DuckDB DESCRIBE returns: column_name, column_type, null, key, default, extra
        columns = [
            {"name": row[0], "type": row[1]}
            for row in described
        ]

        row_count = int(row_count_result[0]) if row_count_result else 0

        return {
            "columns": columns,
            "row_count": row_count,
            "view_name": view_name,
        }
    finally:
        conn.close()


def register_datasets_in_duckdb(
    conn: duckdb.DuckDBPyConnection, datasets: list[dict]
) -> None:
    """
    Register all session datasets as named views in an existing DuckDB connection.

    Each dataset dict has: name (filename), file_path, file_type.
    The view name is derived from the dataset name (same logic as load_dataset_schema).
    Used by execute_query node.
    """
    for dataset in datasets:
        file_path = dataset["file_path"]
        file_type = dataset["file_type"]
        view_name = _safe_view_name(dataset["name"])

        if file_type == "csv":
            conn.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS "
                f"SELECT * FROM read_csv_auto('{file_path}')"
            )
        elif file_type == "json":
            conn.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS "
                f"SELECT * FROM read_json_auto('{file_path}')"
            )
        elif file_type == "xlsx":
            df = _load_excel_as_df(file_path)
            conn.register(view_name, df)
        else:
            raise ValueError(
                f"Unsupported file_type {file_type!r} for dataset {dataset['name']!r}"
            )
