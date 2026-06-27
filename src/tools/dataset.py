"""Local dataset tool — pure, no LLM, no DB.

Loads an uploaded CSV into a pandas DataFrame locally and derives the only two
dataset-derived artefacts that are ever allowed to leave the box toward the LLM:

  * the **schema** — column names + inferred dtypes, and
  * a **bounded sample/summary** — the first `sample_rows` rows plus per-column
    summary stats.

The full DataFrame is never serialized here. This module is deliberately free of
any LLM, DB, or network access so the data-locality guarantee is auditable.
"""

from __future__ import annotations

import math
import os
from typing import Any

import pandas as pd

from config.settings import get_settings
from observability.events import get_logger

logger = get_logger("tools.dataset")

# How many top categories to surface for non-numeric columns in the summary.
_TOP_CATEGORIES = 5


def load_dataframe(file_path: str) -> pd.DataFrame:
    """Read a CSV from the local filesystem into a DataFrame.

    Raises a clear ``ValueError`` on a missing/oversized/unparseable file so the
    graph can surface "Could not read this file as a CSV…" to the user.
    """
    settings = get_settings()

    if not os.path.isfile(file_path):
        raise ValueError(
            "Could not read this file as a CSV: the file was not found."
        )

    size_bytes = os.path.getsize(file_path)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValueError(
            "Could not read this file as a CSV: the upload exceeds the "
            f"{settings.max_upload_mb} MB limit."
        )

    try:
        df = pd.read_csv(file_path)
    except Exception as exc:  # pandas raises a variety of parser errors
        raise ValueError(
            "Could not read this file as a CSV. Please upload a valid, "
            "non-empty CSV file."
        ) from exc

    if df.shape[1] == 0:
        raise ValueError(
            "Could not read this file as a CSV: no columns were detected."
        )

    if len(df) > settings.max_rows:
        raise ValueError(
            "Could not read this file as a CSV: it has more than the "
            f"{settings.max_rows:,} row limit."
        )

    return df


def derive_schema(df: pd.DataFrame) -> list[dict]:
    """Return ``[{"name": col, "dtype": str(df[col].dtype)}, ...]``."""
    return [{"name": str(col), "dtype": str(df[col].dtype)} for col in df.columns]


def _json_safe(value: Any) -> Any:
    """Coerce a single cell to a JSON-serializable value (NaN/NaT → None)."""
    if value is None:
        return None
    # pandas NA / NaT / float NaN
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (int, bool, str)):
        return value
    # Timestamps, numpy scalars, anything else → stringify safely.
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _json_safe(item())
        except (ValueError, TypeError):
            pass
    return str(value)


def _column_summary(series: pd.Series) -> dict:
    """Per-column summary: count, null_count, plus numeric or category stats."""
    non_null = series.dropna()
    summary: dict[str, Any] = {
        "count": int(non_null.shape[0]),
        "null_count": int(series.isna().sum()),
    }

    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        if non_null.shape[0] > 0:
            summary["min"] = _json_safe(non_null.min())
            summary["max"] = _json_safe(non_null.max())
            summary["mean"] = _json_safe(float(non_null.mean()))
        else:
            summary["min"] = None
            summary["max"] = None
            summary["mean"] = None
    else:
        counts = non_null.value_counts().head(_TOP_CATEGORIES)
        summary["top_categories"] = [
            {"value": _json_safe(value), "count": int(count)}
            for value, count in counts.items()
        ]

    return summary


def derive_sample(df: pd.DataFrame, sample_rows: int) -> dict:
    """Return a bounded ``{"preview_rows": [...], "summary": {col: {...}}}``.

    ``preview_rows`` is the first ``sample_rows`` rows as JSON-safe dicts; the
    full DataFrame is never included.
    """
    head = df.head(max(sample_rows, 0))
    preview_rows = [
        {str(col): _json_safe(row[col]) for col in df.columns}
        for _, row in head.iterrows()
    ]

    summary = {str(col): _column_summary(df[col]) for col in df.columns}

    return {"preview_rows": preview_rows, "summary": summary}


def load_and_describe(file_path: str, sample_rows: int | None = None) -> dict:
    """Load a CSV and derive schema + bounded sample for the load_dataset node.

    Returns ``{df, schema, sample, row_count}``. The returned ``df`` is for the
    caller's immediate use only; it is not meant to be carried in graph state.
    """
    if sample_rows is None:
        sample_rows = get_settings().sample_rows

    df = load_dataframe(file_path)
    schema = derive_schema(df)
    sample = derive_sample(df, sample_rows)
    row_count = int(len(df))

    logger.info("dataset.loaded", row_count=row_count, n_cols=len(schema))

    return {"df": df, "schema": schema, "sample": sample, "row_count": row_count}
