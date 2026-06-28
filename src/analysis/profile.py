"""Dataset profiler.

Computes a privacy-safe profile of an uploaded CSV: per-column schema, dtypes,
value ranges / top values, missing counts, distinct counts, plus a small bounded
row sample. This profile (schema + sample + aggregates) is the ONLY data-derived
content ever placed in an LLM prompt — never the full row set.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd


def _json_safe(value: Any) -> Any:
    """Coerce numpy/pandas scalars to JSON-serialisable Python primitives."""
    if value is None:
        return None
    if isinstance(value, float):
        return None if math.isnan(value) else value
    try:
        import numpy as np

        if isinstance(value, np.generic):
            v = value.item()
            if isinstance(v, float) and math.isnan(v):
                return None
            return v
    except Exception:  # pragma: no cover - numpy always present with pandas
        pass
    if pd.isna(value):
        return None
    return value


def build_profile(df: pd.DataFrame, *, sample_rows: int = 20) -> dict:
    """Build the profile dict matching the api.md contract."""
    columns: list[dict] = []
    for name in df.columns:
        series = df[name]
        dtype = str(series.dtype)
        # Normalise textual dtypes ("object" on pandas<3, "str" on pandas>=3) to
        # the contract's "string" label.
        normalised = "string" if dtype in ("object", "str") else dtype
        col: dict[str, Any] = {
            "name": str(name),
            "dtype": normalised,
            "missing_count": int(series.isna().sum()),
            "distinct_count": int(series.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()
            if len(non_null):
                col["min"] = _json_safe(non_null.min())
                col["max"] = _json_safe(non_null.max())
                col["mean"] = _json_safe(round(float(non_null.mean()), 4))
        else:
            top = series.dropna().astype(str).value_counts().head(5).index.tolist()
            col["top_values"] = [str(v) for v in top]
        columns.append(col)

    sample_df = df.head(sample_rows)
    sample = [
        {str(k): _json_safe(v) for k, v in row.items()}
        for row in sample_df.to_dict(orient="records")
    ]

    return {"columns": columns, "sample": sample}
