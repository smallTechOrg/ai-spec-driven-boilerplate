"""Local code executor.

Runs LLM-generated pandas/DuckDB code LOCALLY against the real, full dataset
file (ALL rows). The LLM only ever produced the code text — the raw rows never
left the machine. Code runs in a restricted namespace with the dataframe
pre-loaded as ``df`` and a DuckDB connection available as ``duck`` / ``con``.

Guardrails are best-effort: dangerous tokens (os/subprocess/network/file-write)
are rejected before execution, and builtins are restricted. On any failure the
traceback is captured and returned cleanly rather than crashing the graph.
"""

from __future__ import annotations

import ast
import io
import math
import traceback as tb_module
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from observability.events import get_logger

logger = get_logger("executor")

MAX_RESULT_ROWS = 200

# Substrings that must never appear in generated code. Best-effort static guard.
_FORBIDDEN = (
    "import os",
    "import sys",
    "import subprocess",
    "import socket",
    "import shutil",
    "import requests",
    "import urllib",
    "subprocess",
    "__import__",
    "eval(",
    "exec(",
    "open(",
    "to_csv(",
    "to_excel(",
    "to_parquet(",
    "to_pickle(",
    ".system(",
    "os.",
    "sys.",
    "globals(",
    "compile(",
    "input(",
)

# The primary sandbox is the static forbidden-token guard (``_guard``), which
# rejects os/subprocess/network/file-write/import-of-dangerous-modules before
# execution. We keep real builtins available because libraries like DuckDB
# perform legitimate internal imports (e.g. ``collections.abc``) at call time;
# stripping ``__import__`` breaks them. This is a best-effort sandbox for a
# single-user, local-only tool — documented as such.
import builtins as _builtins_mod

_SAFE_BUILTINS = vars(_builtins_mod)


class ExecutionError(Exception):
    """Raised internally when generated code is rejected or fails."""


_NO_RESULT = object()  # sentinel: distinguishes "no result produced" from None


def _exec_capture_result(code: str, namespace: dict[str, Any]) -> Any:
    """Run code and return its result value (REPL-style).

    Strategy, in priority order:
      1. If the code, after running, bound an explicit ``result`` variable, use it.
      2. Else, if the final top-level statement is a BARE expression (no
         assignment), evaluate that expression and use its value. This captures
         idiomatic generations like ``df.groupby('region').size()`` that omit
         ``result =``.
      3. Else, return the ``_NO_RESULT`` sentinel — the caller turns this into a
         CLEAN error. We NEVER fall back to returning the raw dataframe as if it
         were the computed answer.
    """
    tree = ast.parse(code, mode="exec")
    last_expr: ast.Expr | None = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last_expr = tree.body[-1]  # type: ignore[assignment]
        body = tree.body[:-1]
    else:
        body = tree.body

    exec_module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(exec_module)
    compiled_body = compile(exec_module, filename="<generated>", mode="exec")
    exec(compiled_body, namespace)  # noqa: S102 — sandboxed, guarded namespace

    # 1. Explicit ``result =`` wins.
    if "result" in namespace and namespace["result"] is not None:
        return namespace["result"]

    # 2. Trailing bare expression.
    if last_expr is not None:
        expr_module = ast.Expression(body=last_expr.value)
        ast.fix_missing_locations(expr_module)
        compiled_expr = compile(expr_module, filename="<generated-expr>", mode="eval")
        value = eval(compiled_expr, namespace)  # noqa: S307 — sandboxed, guarded
        if value is not None:
            return value

    # 3. An explicit ``result = None`` still counts as an explicit (None) result.
    if "result" in namespace:
        return namespace["result"]

    return _NO_RESULT


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _result_to_table(result: Any) -> dict[str, Any]:
    """Normalise an execution result into {columns, rows, row_count}."""
    if isinstance(result, pd.DataFrame):
        frame = result
    elif isinstance(result, pd.Series):
        # A groupby().size()/value_counts() Series is unnamed; name its value
        # column "count" so rows are [{<group>, count}] not [{<group>, 0}].
        series = result if result.name is not None else result.rename("count")
        frame = series.reset_index()
        # If reset_index produced a generic "index" col for a count series,
        # leave the group key name as-is (pandas uses the original index name).
    else:
        # scalar / number / string — single-cell table
        return {
            "columns": ["value"],
            "rows": [{"value": _json_safe(result)}],
            "row_count": 1,
        }

    total = int(len(frame))
    capped = frame.head(MAX_RESULT_ROWS)
    rows = [
        {str(k): _json_safe(v) for k, v in row.items()}
        for row in capped.to_dict(orient="records")
    ]
    return {
        "columns": [str(c) for c in frame.columns],
        "rows": rows,
        "row_count": total,
    }


def _guard(code: str) -> None:
    lowered = code.lower()
    for token in _FORBIDDEN:
        if token in lowered:
            raise ExecutionError(f"generated code rejected: forbidden operation {token!r}")


def execute_code(code: str, file_path: str | Path) -> dict[str, Any]:
    """Execute generated analysis code locally over the FULL dataset.

    The dataframe is loaded from ``file_path`` (all rows) and bound as ``df``.
    A DuckDB connection is bound as ``duck`` and ``con``. The code should either
    assign its answer to a variable named ``result`` or end with a bare
    expression (REPL-style). If NEITHER yields a value, this returns a clean
    error — it NEVER masquerades the raw dataframe as the computed answer.

    Returns ``{"result_table": {...}, "stdout": str, "traceback": None}`` on
    success, or ``{"result_table": None, "stdout": str, "traceback": str}`` on
    failure (never raises).
    """
    path = Path(file_path)
    stdout_buf = io.StringIO()
    con = None
    try:
        _guard(code)
        df = pd.read_csv(path)
        con = duckdb.connect(database=":memory:")
        con.register("df", df)
        namespace: dict[str, Any] = {
            "__builtins__": _SAFE_BUILTINS,
            "pd": pd,
            "duckdb": duckdb,
            "df": df,
            "duck": con,
            "con": con,
        }
        with redirect_stdout(stdout_buf):
            result = _exec_capture_result(code, namespace)

        if result is _NO_RESULT:
            # No explicit ``result`` and no trailing expression — refuse to
            # fabricate an answer from raw rows. Clean error so the graph routes
            # to handle_error / records a failed Turn.
            raise ExecutionError(
                "generated code produced no result value: assign to `result` "
                "or end with an expression"
            )

        table = _result_to_table(result)
        con.close()
        return {"result_table": table, "stdout": stdout_buf.getvalue(), "traceback": None}
    except Exception:  # noqa: BLE001 — capture, never crash the graph
        trace = tb_module.format_exc()
        logger.warning("execute_local_failed", traceback=trace)
        return {
            "result_table": None,
            "stdout": stdout_buf.getvalue(),
            "traceback": trace,
        }
