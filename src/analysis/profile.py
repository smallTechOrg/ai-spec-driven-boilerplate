"""Local dataframe profiling — purely local, NEVER calls the LLM.

Produces a row-free schema/profile (column metadata, ranges, samples) that is the
only dataset information ever allowed to reach Gemini.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# How many distinct example values to keep per column. Small + bounded so the
# profile stays a schema summary, never a row dump.
_SAMPLE_VALUES = 5


def load_dataframe(file_path: str, kind: str | None = None) -> pd.DataFrame:
    """Load a CSV or .xlsx file into a pandas DataFrame (local read only)."""
    path = Path(file_path)
    suffix = (kind or path.suffix.lstrip(".")).lower()
    if suffix in ("xlsx", "xls"):
        return pd.read_excel(path, engine="openpyxl")
    return pd.read_csv(path)


def kind_for_filename(filename: str) -> str | None:
    """Map an upload filename to a supported dataset kind, or None if unsupported."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in (".xlsx", ".xls"):
        return "xlsx"
    return None


def _jsonable(value):
    """Coerce a numpy/pandas scalar into a JSON-serialisable Python value."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (np.ndarray,)):
        return [_jsonable(v) for v in value.tolist()]
    return value


def _column_profile(series: pd.Series) -> dict:
    dtype = str(series.dtype)
    non_null = int(series.notna().sum())
    n_unique = int(series.nunique(dropna=True))

    col_min = None
    col_max = None
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
        if non_null:
            col_min = _jsonable(series.min())
            col_max = _jsonable(series.max())

    sample_values = [
        _jsonable(v) for v in series.dropna().unique()[:_SAMPLE_VALUES].tolist()
    ]

    return {
        "name": str(series.name),
        "dtype": dtype,
        "non_null": non_null,
        "n_unique": n_unique,
        "min": col_min,
        "max": col_max,
        "sample_values": sample_values,
    }


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Return a bounded, row-free profile of a dataframe.

    Shape: {columns: [{name, dtype, non_null, n_unique, min, max, sample_values}],
            row_count, column_count}
    """
    columns = [_column_profile(df[col]) for col in df.columns]
    return {
        "columns": columns,
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
    }


def profile_file(file_path: str, kind: str | None = None) -> dict:
    """Load a file locally and profile it. No rows leave this function."""
    df = load_dataframe(file_path, kind=kind)
    return profile_dataframe(df)
