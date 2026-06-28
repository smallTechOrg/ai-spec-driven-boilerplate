"""Local pandas code executor (LLM-generated code execution, agentic pattern #22).

Runs a generated snippet against the FULL in-memory DataFrame in a restricted
namespace. This is NOT a security sandbox (single trusted local user — see
architecture.md safety posture); it is pragmatic guardrails:

- restricted globals: only ``pd``, ``np``, the named frame ``df``, and a small
  builtins allowlist;
- a wall-clock timeout (default 60s);
- a head-truncated / size-capped result preview.

The full DataFrame is NEVER serialized into the preview or anywhere that reaches
the LLM. Errors are captured into the result, never raised out — they feed the
refine loop.
"""
from __future__ import annotations

import io
import threading
from contextlib import redirect_stdout
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

DEFAULT_TIMEOUT_SECONDS = 60
# Head cap for any tabular result preview (rows) and overall char cap.
PREVIEW_MAX_ROWS = 20
PREVIEW_MAX_CHARS = 4000

_ALLOWED_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "round": round,
    "sorted": sorted,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "print": print,
    "True": True,
    "False": False,
    "None": None,
}


@dataclass
class ExecutionResult:
    result_preview: str | None = None
    stdout: str = ""
    error: str | None = None
    raw_result_type: str | None = field(default=None)

    def to_dict(self) -> dict:
        return {
            "result_preview": self.result_preview,
            "stdout": self.stdout,
            "error": self.error,
            "raw_result_type": self.raw_result_type,
        }


def _truncate(text: str) -> str:
    if len(text) > PREVIEW_MAX_CHARS:
        return text[:PREVIEW_MAX_CHARS] + "\n... [truncated]"
    return text


def _preview(result: object) -> str:
    """Produce a head-truncated, size-capped preview. Never the full frame."""
    if result is None:
        return "None"
    if isinstance(result, pd.DataFrame):
        head = result.head(PREVIEW_MAX_ROWS)
        text = head.to_string()
        if len(result) > PREVIEW_MAX_ROWS:
            text += f"\n... [{len(result)} rows total, showing first {PREVIEW_MAX_ROWS}]"
        return _truncate(text)
    if isinstance(result, pd.Series):
        head = result.head(PREVIEW_MAX_ROWS)
        text = head.to_string()
        if len(result) > PREVIEW_MAX_ROWS:
            text += f"\n... [{len(result)} entries total, showing first {PREVIEW_MAX_ROWS}]"
        return _truncate(text)
    return _truncate(str(result))


def execute_pandas(
    code: str,
    df: pd.DataFrame,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> ExecutionResult:
    """Run ``code`` with ``df`` in scope; the snippet assigns to ``result``.

    Returns an ExecutionResult; never raises out (errors are captured).
    """
    namespace: dict = {
        "__builtins__": _ALLOWED_BUILTINS,
        "pd": pd,
        "np": np,
        "df": df,
    }
    stdout_buf = io.StringIO()
    container: dict = {}

    def _run() -> None:
        try:
            with redirect_stdout(stdout_buf):
                exec(code, namespace)  # noqa: S102 — trusted single-user code
            if "result" in namespace:
                container["has_result"] = True
                container["result"] = namespace["result"]
        except Exception as exc:  # noqa: BLE001 — capture, never crash the request
            container["error"] = f"{type(exc).__name__}: {exc}"

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout)

    stdout = stdout_buf.getvalue()
    if len(stdout) > PREVIEW_MAX_CHARS:
        stdout = stdout[:PREVIEW_MAX_CHARS] + "\n... [truncated]"

    if thread.is_alive():
        return ExecutionResult(
            error=f"Execution timed out after {timeout}s",
            stdout=stdout,
        )

    if "error" in container:
        return ExecutionResult(error=container["error"], stdout=stdout)

    if not container.get("has_result"):
        return ExecutionResult(
            error="The snippet did not assign a variable named `result`.",
            stdout=stdout,
        )

    result = container.get("result")
    return ExecutionResult(
        result_preview=_preview(result),
        stdout=stdout,
        error=None,
        raw_result_type=type(result).__name__,
    )
