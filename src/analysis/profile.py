"""Privacy-safe dataset profiler.

This module is the ONLY place sample rows are produced. The privacy invariant
(architecture.md, agent.md) requires that at most ``MAX_SAMPLE_ROWS`` raw rows
ever reach the LLM. Every other layer consumes the profile built here; no layer
serializes the full DataFrame for the model.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

# The single source of truth for the sample-row cap (privacy invariant).
MAX_SAMPLE_ROWS = 5

# Cap on distinct top-value strings reported per categorical column.
_MAX_TOP_VALUES = 5


def load_csv(path: str) -> pd.DataFrame:
    """Load a CSV file from disk into a DataFrame.

    Raises on an unparseable file so the caller can surface BAD_UPLOAD.
    """
    return pd.read_csv(path)


def _clean(value: Any) -> Any:
    """Make a value JSON-serializable and free of NaN/inf."""
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.ndarray, list)):
        return [_clean(v) for v in value]
    if pd.isna(value) if np.isscalar(value) else False:
        return None
    return value


def build_profile(df: pd.DataFrame) -> dict[str, Any]:
    """Build a privacy-safe profile: per-column schema/stats + a <=5-row sample.

    Returns a JSON-serializable dict with ``columns``, ``numeric_stats``,
    ``sample`` (<= MAX_SAMPLE_ROWS rows), and ``row_count``.
    """
    columns: list[dict[str, Any]] = []
    numeric_stats: dict[str, dict[str, Any]] = {}

    for name in df.columns:
        col = df[name]
        dtype = str(col.dtype)
        missing = int(col.isna().sum())
        distinct = int(col.nunique(dropna=True))

        top_values: list[Any] = []
        try:
            vc = col.value_counts(dropna=True).head(_MAX_TOP_VALUES)
            top_values = [_clean(v) for v in vc.index.tolist()]
        except Exception:
            top_values = []

        columns.append(
            {
                "name": str(name),
                "dtype": dtype,
                "missing": missing,
                "distinct": distinct,
                "top": top_values,
            }
        )

        if pd.api.types.is_numeric_dtype(col):
            numeric_stats[str(name)] = {
                "min": _clean(col.min()),
                "max": _clean(col.max()),
                "mean": _clean(col.mean()),
            }

    sample = _build_sample(df)

    return {
        "row_count": int(len(df)),
        "columns": columns,
        "numeric_stats": numeric_stats,
        "sample": sample,
    }


def _build_sample(df: pd.DataFrame) -> list[dict[str, Any]]:
    """The ONLY producer of raw sample rows, hard-capped at MAX_SAMPLE_ROWS."""
    head = df.head(MAX_SAMPLE_ROWS)
    rows: list[dict[str, Any]] = []
    for _, row in head.iterrows():
        rows.append({str(k): _clean(v) for k, v in row.items()})
    # Defensive: never exceed the cap regardless of caller misuse.
    return rows[:MAX_SAMPLE_ROWS]


def profile_csv(path: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load + profile a CSV. Returns (DataFrame, profile)."""
    df = load_csv(path)
    return df, build_profile(df)
