"""Local code executor.

Runs LLM-generated pandas code LOCALLY against the FULL DataFrame in a
constrained namespace. The LLM never sees raw rows — only the executor does, and
only on the local machine. The generated code must assign its answer to a variable
named ``result`` and may assign a Vega-Lite spec to ``chart_spec``.

Builtins are restricted: no open/import/eval/exec/network/filesystem access.
"""
from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd


class ExecutionError(Exception):
    """Raised when the generated code fails to run or produce a usable result."""


# A small, explicit allowlist of safe builtins for analysis code.
_SAFE_BUILTINS = {
    "abs": abs, "min": min, "max": max, "sum": sum, "len": len,
    "round": round, "sorted": sorted, "range": range, "enumerate": enumerate,
    "zip": zip, "list": list, "dict": dict, "set": set, "tuple": tuple,
    "float": float, "int": int, "str": str, "bool": bool, "map": map,
    "filter": filter, "any": any, "all": all,
}


def _json_safe(value: Any) -> Any:
    """Coerce execution output to a JSON-serialisable structure."""
    if value is None:
        return None
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, pd.Series):
        return {str(k): _json_safe(v) for k, v in value.to_dict().items()}
    if isinstance(value, pd.DataFrame):
        return [_json_safe(r) for r in value.to_dict(orient="records")]
    try:
        import numpy as np

        if isinstance(value, np.generic):
            return _json_safe(value.item())
        if isinstance(value, np.ndarray):
            return [_json_safe(v) for v in value.tolist()]
    except Exception:  # pragma: no cover
        pass
    if pd.isna(value):
        return None
    return str(value)


def execute_code(code: str, df: pd.DataFrame) -> dict:
    """Execute generated code against ``df``; return {result, chart_spec}.

    Raises ExecutionError on any failure so the agentic loop can regenerate.
    """
    namespace: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "pd": pd,
        "df": df,
        "result": None,
        "chart_spec": None,
    }
    try:
        exec(compile(code, "<analysis>", "exec"), namespace)  # noqa: S102
    except Exception as exc:
        raise ExecutionError(f"{type(exc).__name__}: {exc}") from exc

    if namespace.get("result") is None:
        raise ExecutionError("Code did not assign a non-empty `result` variable.")

    result = _json_safe(namespace["result"])
    if result is None or (isinstance(result, (list, dict)) and len(result) == 0):
        raise ExecutionError("`result` was empty after execution.")

    chart_spec = namespace.get("chart_spec")
    chart_spec = _json_safe(chart_spec) if chart_spec is not None else None

    # Ensure the result is genuinely JSON-serialisable.
    try:
        json.dumps(result)
        if chart_spec is not None:
            json.dumps(chart_spec)
    except (TypeError, ValueError) as exc:
        raise ExecutionError(f"Result not JSON-serialisable: {exc}") from exc

    return {"result": result, "chart_spec": chart_spec}
