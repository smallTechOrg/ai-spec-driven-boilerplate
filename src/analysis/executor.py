"""The sandboxed local pandas executor — the privacy boundary.

This is the ONLY code that touches raw data rows. It runs an LLM-generated pandas
snippet in a restricted namespace with `df` bound to the dataset's dataframe, a
whitelisted import set (pandas, numpy), and NO filesystem/network/`__import__`
builtins. The generated code assigns its answer to a `result` variable; we capture
that into a BOUNDED summary (scalars verbatim; large frames truncated to head +
shape). Raw rows never leave the process — only the bounded summary is returned
and (later) shown to the LLM.

Code exceptions are CAPTURED into an error string, never raised.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Max rows of any frame/series we will surface in a result summary.
_MAX_SUMMARY_ROWS = 50

_CODE_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)

# Call targets (by bare name) the generated code may never invoke. These are the
# classic escape/introspection/IO primitives. `pd`/`np` are pre-bound, so the
# generated code never needs import/eval/etc.
_DENIED_CALL_NAMES = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "input",
        "exit",
        "quit",
        "breakpoint",
        "memoryview",
    }
)


class _GuardViolation(Exception):
    """Raised internally by the AST guard; converted to a clean exec_error."""


def _is_dunder(name: str) -> bool:
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


def check_code_is_safe(code: str) -> str | None:
    """Static AST guard, run BEFORE exec. The REAL sandbox boundary.

    Returns a human-readable reason string if `code` contains a disallowed
    construct (so the caller can degrade honestly), else None. Restricting
    `__builtins__` alone is NOT a sandbox — `().__class__.__bases__[0].
    __subclasses__()` reaches subprocess.Popen etc. We therefore reject, before
    any execution:

      * ANY dunder attribute access (`__class__`, `__subclasses__`, `__bases__`,
        `__mro__`, `__globals__`, `__builtins__`, `__import__`, `__dict__`, ...),
      * `import` / `from ... import` statements (pd/np are pre-bound),
      * calls to known escape/introspection/IO primitives by name.
    """
    try:
        tree = ast.parse(code or "")
    except SyntaxError as exc:
        return f"blocked: could not parse code ({exc})"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return "blocked: disallowed construct 'import'"
        if isinstance(node, ast.Attribute) and _is_dunder(node.attr):
            return f"blocked: disallowed dunder attribute '{node.attr}'"
        # Defensive: dunder names referenced bare (e.g. via comprehension targets).
        if isinstance(node, ast.Name) and _is_dunder(node.id):
            return f"blocked: disallowed dunder name '{node.id}'"
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _DENIED_CALL_NAMES:
                return f"blocked: disallowed call '{func.id}'"
    return None

# Builtins the generated code is allowed to use. Deliberately excludes open,
# __import__, eval, exec, compile, input, etc.
_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


@dataclass
class ExecutionResult:
    """Outcome of running generated code. Exactly one of summary/error is set."""

    summary: dict | None = None
    error: str | None = None


def extract_code(text: str) -> str:
    """Pull the python snippet from an LLM response (fenced block preferred)."""
    match = _CODE_FENCE.search(text or "")
    if match:
        return match.group(1).strip()
    return (text or "").strip()


def _jsonable(value):
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if (f != f) else f  # drop NaN
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (np.ndarray,)):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, float) and value != value:  # NaN
        return None
    return value


def summarize_result(result) -> dict:
    """Bound a computed result into a compact, JSON-serialisable summary."""
    if isinstance(result, pd.DataFrame):
        truncated = len(result) > _MAX_SUMMARY_ROWS
        head = result.head(_MAX_SUMMARY_ROWS)
        records = [
            {str(k): _jsonable(v) for k, v in row.items()}
            for row in head.to_dict(orient="records")
        ]
        return {
            "type": "dataframe",
            "shape": [int(result.shape[0]), int(result.shape[1])],
            "columns": [str(c) for c in result.columns],
            "rows": records,
            "truncated": truncated,
        }
    if isinstance(result, pd.Series):
        truncated = len(result) > _MAX_SUMMARY_ROWS
        head = result.head(_MAX_SUMMARY_ROWS)
        return {
            "type": "series",
            "length": int(len(result)),
            "name": None if result.name is None else str(result.name),
            "values": {str(k): _jsonable(v) for k, v in head.to_dict().items()},
            "truncated": truncated,
        }
    return {"type": "scalar", "value": _jsonable(result)}


def execute_code(code: str, df: pd.DataFrame) -> ExecutionResult:
    """Run `code` in a restricted namespace with `df` bound. Captures errors.

    The STATIC AST guard (`check_code_is_safe`) is the real boundary and runs
    BEFORE exec; the restricted `__builtins__` is defense-in-depth only.
    """
    violation = check_code_is_safe(code)
    if violation is not None:
        return ExecutionResult(error=violation)

    namespace: dict = {
        "__builtins__": dict(_SAFE_BUILTINS),
        "pd": pd,
        "np": np,
        "df": df,
    }
    try:
        exec(code, namespace)  # noqa: S102 - AST-guarded + restricted builtins, no df leak
    except Exception as exc:  # capture, never raise
        return ExecutionResult(error=f"{type(exc).__name__}: {exc}")

    if "result" not in namespace:
        return ExecutionResult(
            error="Generated code did not assign a `result` variable."
        )
    try:
        summary = summarize_result(namespace["result"])
    except Exception as exc:
        return ExecutionResult(error=f"Could not summarize result: {exc}")
    return ExecutionResult(summary=summary)
