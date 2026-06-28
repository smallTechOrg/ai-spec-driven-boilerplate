"""Local dataset profiler.

Loads a tabular file with pandas and derives a privacy-safe profile: per-column
name/dtype/distinct/null/range plus a tiny capped sample. The TRUE row count is
computed over ALL rows here — the LLM never sees the full row set (see
``src/llm/context.py`` for the single chokepoint that builds the LLM payload).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_SAMPLE_ROWS = 5


def _json_safe(value: Any) -> Any:
    """Coerce a pandas/numpy scalar into a plain JSON-serialisable value."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _column_profile(series: pd.Series) -> dict[str, Any]:
    dtype = str(series.dtype)
    null_count = int(series.isna().sum())
    non_null = int(series.notna().sum())
    distinct_count = int(series.nunique(dropna=True))

    col: dict[str, Any] = {
        "name": str(series.name),
        "dtype": dtype,
        "non_null": non_null,
        "null_count": null_count,
        "distinct_count": distinct_count,
        "min": None,
        "max": None,
        "sample_values": [],
    }

    is_numeric = pd.api.types.is_numeric_dtype(series)
    is_datetime = pd.api.types.is_datetime64_any_dtype(series)

    if is_numeric or is_datetime:
        non_na = series.dropna()
        if not non_na.empty:
            col["min"] = _json_safe(non_na.min())
            col["max"] = _json_safe(non_na.max())

    # Free-text / categorical columns report a few distinct sample values only —
    # never a full value dump.
    distinct_vals = series.dropna().unique()[:DEFAULT_SAMPLE_ROWS]
    col["sample_values"] = [_json_safe(v) for v in distinct_vals]
    return col


def profile_dataframe(
    df: pd.DataFrame, *, sample_rows: int = DEFAULT_SAMPLE_ROWS
) -> dict[str, Any]:
    """Profile an already-loaded dataframe (row_count over ALL rows)."""
    profile = [_column_profile(df[col]) for col in df.columns]
    head = df.head(sample_rows)
    sample = [
        {str(k): _json_safe(v) for k, v in row.items()}
        for row in head.to_dict(orient="records")
    ]
    return {
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "profile": profile,
        "sample_rows": sample,
    }


def profile_csv(
    file_path: str | Path, *, sample_rows: int = DEFAULT_SAMPLE_ROWS
) -> dict[str, Any]:
    """Load a CSV from disk and return its full profile + capped sample.

    Returns a dict: {row_count, column_count, profile: [...], sample_rows: [...]}.
    Raises ``ValueError`` with a readable message on an unparseable file.
    """
    path = Path(file_path)
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001 — surface a clean, readable error
        raise ValueError(f"could not parse file: {exc}") from exc
    if df.shape[1] == 0:
        raise ValueError("could not parse file: no columns detected")
    return profile_dataframe(df, sample_rows=sample_rows)
