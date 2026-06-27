"""Local profiler — derives the compact ``DataProfile`` near the privacy boundary.

Reads the LOCAL CSV with pandas and returns ONLY a small derived dict: schema,
row count, per-column summary statistics, and at most 5 truncated example values
per column. The raw DataFrame stays in local scope and is never returned. This is
the only data-bearing artifact allowed near the LLM prompt.
"""

import math

import pandas as pd
from pandas.api import types as ptypes

from datasets.store import dataset_path, _friendly_dtype, DatasetError
from observability.events import get_logger

logger = get_logger("datasets.profiler")

# Caps that keep the profile small and prevent any full column/row from leaking.
_MAX_EXAMPLES = 5
_EXAMPLE_STR_CAP = 60
_TOP_CATEGORIES = 10


def _cap_value(value: object) -> object:
    """Return a JSON-friendly, length-capped representation of a single value."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (int, bool)):
        return value
    if isinstance(value, float):
        return round(value, 6)
    s = str(value)
    if len(s) > _EXAMPLE_STR_CAP:
        return s[:_EXAMPLE_STR_CAP] + "…"
    return s


def _safe_float(value: object) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def build_profile(dataset_id: str) -> dict:
    """Compute the derived :class:`DataProfile` for a dataset from its local CSV.

    Returns a dict with shape::

        {
          "row_count": int,
          "columns": [{"name", "dtype", "friendly_dtype"}, ...],
          "stats":    {col: {...per-column summary stats...}, ...},
          "examples": {col: [≤5 truncated example values], ...},
        }

    Numeric columns get min/max/mean/median/std/null_count; non-numeric columns get
    distinct_count + capped top values & counts. No raw row is ever returned.

    Raises :class:`DatasetError` with human-readable copy if the local file is
    missing or unreadable.
    """
    path = dataset_path(dataset_id)
    if not path.exists():
        raise DatasetError("Dataset not found or unreadable.")

    try:
        df = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("profile_read_failed", dataset_id=dataset_id, error=str(exc))
        raise DatasetError("Dataset not found or unreadable.") from exc

    columns: list[dict] = []
    stats: dict[str, dict] = {}
    examples: dict[str, list] = {}

    for col in df.columns:
        series = df[col]
        name = str(col)
        columns.append(
            {
                "name": name,
                "dtype": str(series.dtype),
                "friendly_dtype": _friendly_dtype(series.dtype),
            }
        )

        null_count = int(series.isna().sum())

        if ptypes.is_numeric_dtype(series) and not ptypes.is_bool_dtype(series):
            stats[name] = {
                "kind": "numeric",
                "min": _safe_float(series.min()),
                "max": _safe_float(series.max()),
                "mean": _safe_float(series.mean()),
                "median": _safe_float(series.median()),
                "std": _safe_float(series.std()),
                "null_count": null_count,
            }
        else:
            non_null = series.dropna()
            distinct_count = int(non_null.nunique())
            top = non_null.value_counts().head(_TOP_CATEGORIES)
            top_values = [
                {"value": _cap_value(idx), "count": int(cnt)}
                for idx, cnt in top.items()
            ]
            stats[name] = {
                "kind": "categorical",
                "distinct_count": distinct_count,
                "top_values": top_values,
                "null_count": null_count,
            }

        # ≤5 truncated example values per column (deduplicated, non-null first).
        example_vals = [
            _cap_value(v) for v in series.dropna().unique()[:_MAX_EXAMPLES]
        ]
        examples[name] = example_vals

    profile = {
        "row_count": int(len(df)),
        "columns": columns,
        "stats": stats,
        "examples": examples,
    }

    logger.info(
        "profile_built",
        dataset_id=dataset_id,
        row_count=profile["row_count"],
        n_columns=len(columns),
    )

    # The raw DataFrame `df` goes out of scope here; only the derived dict returns.
    return profile
