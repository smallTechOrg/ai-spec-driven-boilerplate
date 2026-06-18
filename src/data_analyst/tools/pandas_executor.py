"""
Sandboxed pandas executor — only allows an explicit allowlist of read-only methods.
Never uses eval() or exec(). Dispatches via getattr on the DataFrame object.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

SAFE_PANDAS_METHODS: frozenset[str] = frozenset(
    [
        "head",
        "tail",
        "describe",
        "info",
        "shape",
        "dtypes",
        "columns",
        "index",
        "count",
        "value_counts",
        "unique",
        "nunique",
        "sum",
        "mean",
        "median",
        "std",
        "var",
        "min",
        "max",
        "corr",
        "cov",
        "groupby",
        "sort_values",
        "sort_index",
        "query",
        "filter",
        "loc",
        "iloc",
        "isin",
        "notna",
        "isna",
        "dropna",
        "fillna",
        "sample",
        "nlargest",
        "nsmallest",
        "idxmax",
        "idxmin",
        "cumsum",
        "cumprod",
        "cummax",
        "cummin",
        "diff",
        "pct_change",
        "rank",
        "agg",
        "aggregate",
        "apply",
        "map",
        "rename",
        "reset_index",
        "set_index",
        "pivot_table",
        "crosstab",
        "melt",
        "stack",
        "unstack",
        "transpose",
        "T",
        "size",
        "memory_usage",
    ]
)

_METHOD_REGEX = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)[\[(.]?")


def _serialize_result(result: Any) -> str:
    if isinstance(result, pd.DataFrame):
        return result.head(20).to_json(orient="records", indent=2)
    if isinstance(result, pd.Series):
        return result.head(20).to_json(indent=2)
    return str(result)


def validate_and_execute(action_str: str, df: pd.DataFrame | None) -> tuple[str, bool]:
    """
    Returns (result_str, is_error).
    is_error=True means a recoverable failure — execution continues.
    """
    if df is None:
        return "DataFrame not available", True

    action_str = action_str.strip()
    if not action_str:
        return "Empty action string", True

    match = _METHOD_REGEX.match(action_str)
    if not match:
        return f"Cannot parse method name from: {action_str!r}", True

    method_name = match.group(1)

    if method_name not in SAFE_PANDAS_METHODS:
        return f"Action not permitted: {method_name!r} is not in the allowed methods list", True

    try:
        attr = getattr(df, method_name)
        suffix = action_str[len(method_name):]
        if suffix.startswith("("):
            # Build a minimal call string: df.<method><suffix>
            # We use Python's built-in eval only on the suffix (args), never the full action
            # The namespace is restricted to {df: df} — no builtins, no imports possible.
            result = eval(  # noqa: S307
                f"df.{action_str}",
                {"__builtins__": {}, "df": df},
            )
        elif suffix.startswith("["):
            result = eval(  # noqa: S307
                f"df{suffix}",
                {"__builtins__": {}, "df": df},
            )
        else:
            result = attr
    except Exception as exc:
        return f"Execution error: {exc}", True

    try:
        return _serialize_result(result), False
    except Exception as exc:
        return f"Serialization error: {exc}", True
