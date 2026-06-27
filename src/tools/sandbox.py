"""Local restricted-namespace sandbox for LLM-proposed pandas code.

Threat model: the agent's *own* LLM-proposed code over the user's local data
(see spec/architecture.md "Local code sandbox" / Assumed). This is an in-process
restricted-namespace ``exec`` with a thread-based wall-clock timeout and a
stripped builtins dict — NOT an OS-level container.

Contract:
- The proposed ``code`` must assign its answer to a variable named ``result``.
- ``run(code, df)`` returns ``{"ok": True, "result": <json-coercible value>}``
  on success, or ``{"ok": False, "error": ..., "traceback_summary": ...}`` on
  any failure (exception, missing ``result``, forbidden op, or timeout).
- ``run`` NEVER raises and NEVER leaks a full traceback as the primary error.
"""

from __future__ import annotations

import math
import threading
import time
import traceback
from typing import Any

import pandas as pd

from src.config.settings import get_settings
from src.observability.events import get_logger

logger = get_logger("sandbox")

# Small allow-list of safe builtins exposed inside the sandbox namespace.
# Deliberately EXCLUDES __import__, open, eval, exec, compile, globals, locals,
# vars, getattr/setattr/delattr, input, etc. — anything that grants import,
# filesystem, network, or arbitrary-attribute access.
_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
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


def _default_timeout() -> float:
    # sandbox_timeout_s is added to Settings by a sibling slice; tolerate its
    # absence when this module is exercised standalone.
    return float(getattr(get_settings(), "sandbox_timeout_s", 10.0))


def _coerce(value: Any) -> Any:
    """Coerce an exec result into a JSON-serializable value.

    Handles numpy scalars, pandas Series/DataFrame, NaN/NaT, and nested
    containers. Anything unrecognised falls back to ``str(value)``.
    """
    # None passes straight through.
    if value is None:
        return None

    # pandas / numpy NA (covers NaN, NaT, pd.NA) on scalar-ish values.
    try:
        if pd.api.types.is_scalar(value) and pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    # Plain JSON-native scalars.
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, str):
        return value

    # pandas DataFrame → list-of-row-dicts.
    if isinstance(value, pd.DataFrame):
        return _coerce(value.to_dict(orient="records"))

    # pandas Series → {index: value} dict.
    if isinstance(value, pd.Series):
        return _coerce(value.to_dict())

    # pandas Index → list.
    if isinstance(value, pd.Index):
        return _coerce(list(value))

    # numpy scalar (has .item()) → native python scalar.
    item = getattr(value, "item", None)
    if callable(item) and getattr(value, "ndim", None) == 0:
        try:
            return _coerce(value.item())
        except (ValueError, TypeError):
            pass

    # numpy array → list.
    tolist = getattr(value, "tolist", None)
    if callable(tolist) and not isinstance(value, (str, bytes)):
        try:
            return _coerce(tolist())
        except (ValueError, TypeError):
            pass

    # Containers — recurse.
    if isinstance(value, dict):
        return {str(_coerce_key(k)): _coerce(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_coerce(v) for v in value]

    # Fallback: stringify anything we don't explicitly understand.
    return str(value)


def _coerce_key(key: Any) -> Any:
    coerced = _coerce(key)
    return coerced if isinstance(coerced, (str, int, float, bool)) or coerced is None else str(coerced)


def _summarize_error(exc: BaseException) -> tuple[str, str]:
    """Return (short_error, last_traceback_line) for a structured error."""
    short = f"{type(exc).__name__}: {exc}".strip()
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    last = tb_lines[-1].strip() if tb_lines else short
    return short, last


def run(code: str, df: "pd.DataFrame", timeout_s: float | None = None) -> dict[str, Any]:
    """Execute LLM-proposed pandas ``code`` over ``df`` in a restricted namespace.

    Returns a structured dict: ``{"ok": True, "result": ...}`` on success, or
    ``{"ok": False, "error": ..., "traceback_summary": ...}`` on any failure.
    Never raises.
    """
    timeout = _default_timeout() if timeout_s is None else float(timeout_s)
    started = time.perf_counter()

    # Restricted namespace: only df, pd, and the safe-builtins allow-list.
    namespace: dict[str, Any] = {
        "__builtins__": dict(_SAFE_BUILTINS),
        "df": df,
        "pd": pd,
    }

    outcome: dict[str, Any] = {}

    def _worker() -> None:
        try:
            exec(code, namespace)  # noqa: S102 — intentional restricted exec
            if "result" not in namespace:
                outcome["error"] = (
                    "Code did not assign a 'result' variable."
                )
                outcome["traceback_summary"] = "NameError: 'result' was never assigned"
                outcome["ok"] = False
                return
            outcome["result"] = _coerce(namespace["result"])
            outcome["ok"] = True
        except BaseException as exc:  # noqa: BLE001 — sandbox must contain everything
            short, last = _summarize_error(exc)
            outcome["error"] = short
            outcome["traceback_summary"] = last
            outcome["ok"] = False

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join(timeout)

    duration_ms = round((time.perf_counter() - started) * 1000.0, 3)

    if worker.is_alive():
        # Wall-clock timeout. The daemon thread is abandoned (cannot be force
        # killed in CPython); the structured timeout error is returned.
        logger.info("code.executed", ok=False, duration_ms=duration_ms, reason="timeout")
        return {
            "ok": False,
            "error": f"Execution exceeded the {timeout:g}s wall-clock timeout.",
            "traceback_summary": "TimeoutError: sandbox wall-clock timeout",
        }

    if outcome.get("ok"):
        logger.info("code.executed", ok=True, duration_ms=duration_ms)
        return {"ok": True, "result": outcome["result"]}

    logger.info("code.executed", ok=False, duration_ms=duration_ms)
    return {
        "ok": False,
        "error": outcome.get("error", "Unknown execution error."),
        "traceback_summary": outcome.get("traceback_summary", ""),
    }
