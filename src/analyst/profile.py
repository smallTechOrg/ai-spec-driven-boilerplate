"""CSV profiling.

Phase 1: the minimal, privacy-safe profile the prompt needs — row_count,
schema ([{name, dtype}]) and a small sample (<= 20 rows).

Phase 2: the FULL per-column auto-profile (type category, distinct, missing,
min/max range, a few example values) computed LOCALLY over the whole file.
PRIVACY: the auto-profile is derived statistics + a tiny set of example values
only — it is for the UI/DB and is NEVER fed to the LLM. The full column data
never leaves this process.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from pandas.api import types as pdt

MAX_SAMPLE_ROWS = 20
MAX_PROFILE_EXAMPLES = 5


@dataclass
class CsvProfile:
    row_count: int
    schema: list[dict]          # [{name, dtype}]
    sample_rows: list[dict]     # <= 20 rows as JSON-safe records


def _json_safe_records(df: pd.DataFrame) -> list[dict]:
    """Coerce a DataFrame to JSON-safe records (NaN -> None, native types)."""
    safe = df.astype(object).where(pd.notnull(df), None)
    records: list[dict] = []
    for row in safe.to_dict(orient="records"):
        records.append({k: _coerce(v) for k, v in row.items()})
    return records


def _coerce(value):
    if value is None:
        return None
    # numpy scalars -> python scalars
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            return str(value)
    if isinstance(value, (int, float, bool, str)):
        return value
    return str(value)


def profile_csv(path: str) -> CsvProfile:
    """Read the CSV once and derive the minimal, LLM-safe profile.

    Raises ValueError if the file is empty or unparseable by pandas.
    """
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("CSV file is empty or has no columns") from exc
    except Exception as exc:  # malformed CSV
        raise ValueError(f"Could not parse CSV: {exc}") from exc

    if df.shape[1] == 0:
        raise ValueError("CSV file has no columns")

    schema = [{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns]
    sample = _json_safe_records(df.head(MAX_SAMPLE_ROWS))
    return CsvProfile(row_count=int(len(df)), schema=schema, sample_rows=sample)


def _type_category(series: pd.Series) -> str:
    """Coarse, UI-friendly type bucket for a column."""
    dtype = series.dtype
    if pdt.is_bool_dtype(dtype):
        return "boolean"
    if pdt.is_numeric_dtype(dtype):
        return "numeric"
    if pdt.is_datetime64_any_dtype(dtype):
        return "datetime"
    return "categorical"


def _maybe_datetime(series: pd.Series) -> pd.Series | None:
    """Best-effort parse of an object column to datetime; None if it doesn't fit.

    Vectorized — no per-row work. Treated as datetime only if a clear majority
    of non-null values parse cleanly (avoids misclassifying free text).
    """
    non_null = series.dropna()
    if non_null.empty:
        return None
    parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
    ok = parsed.notna().mean()
    if ok >= 0.9:
        return parsed
    return None


def _profile_column(series: pd.Series) -> dict:
    """Vectorized per-column profile. Safe for large columns (no row iteration)."""
    non_null = series.dropna()
    missing = int(series.isna().sum())
    distinct = int(series.nunique(dropna=True))

    category = _type_category(series)
    value_series: pd.Series = non_null
    col_min = None
    col_max = None

    if category == "categorical":
        # Object columns may actually be dates stored as strings.
        parsed = _maybe_datetime(series)
        if parsed is not None:
            category = "datetime"
            value_series = parsed

    if category in ("numeric", "datetime") and not value_series.empty:
        try:
            col_min = _coerce(value_series.min())
            col_max = _coerce(value_series.max())
        except (TypeError, ValueError):
            col_min = col_max = None

    examples = [
        _coerce(v)
        for v in non_null.drop_duplicates().head(MAX_PROFILE_EXAMPLES).tolist()
    ]

    return {
        "name": str(series.name),
        "dtype": str(series.dtype),
        "type_category": category,
        "missing": missing,
        "distinct": distinct,
        "min": col_min,
        "max": col_max,
        "examples": examples,
    }


def compute_profile(path: str) -> list[dict]:
    """Read the FULL file locally and compute a per-column auto-profile.

    Returns a list of per-column dicts:
        {name, dtype, type_category, missing, distinct, min, max, examples}

    Vectorized pandas only — suitable for large files (hundreds of thousands of
    rows). PRIVACY: derived stats + a few example values only; the full column is
    never serialized and never reaches the LLM.

    Raises ValueError if the file is empty or unparseable (same contract as
    profile_csv) so callers can distinguish a bad file from a degraded profile.
    """
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("CSV file is empty or has no columns") from exc
    except Exception as exc:  # malformed CSV
        raise ValueError(f"Could not parse CSV: {exc}") from exc

    if df.shape[1] == 0:
        raise ValueError("CSV file has no columns")

    return [_profile_column(df[col]) for col in df.columns]
