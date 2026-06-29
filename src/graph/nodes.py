"""LangGraph nodes for the CSV analysis agent."""

import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import structlog

from graph.state import AgentState
from llm.client import LLMClient

logger = structlog.get_logger()

_CODE_GEN_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "code_gen.md"
_FORMAT_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "format_response.md"

_EXEC_TIMEOUT_SECONDS = 30


def _load_prompt(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


# ---------------------------------------------------------------------------
# profile_data — pure pandas, NO LLM call
# ---------------------------------------------------------------------------

def profile_data(state: AgentState) -> AgentState:
    """Compute per-column statistics for the uploaded CSV. No LLM call."""
    t0 = time.time()
    session_id = state.get("session_id", "")
    log = logger.bind(node="profile_data", session_id=session_id)
    log.info("node_enter")

    try:
        files = state.get("uploaded_files", [])
        if not files:
            raise ValueError("No uploaded files in state")

        file_info = files[0]
        file_path = file_info["path"]

        df = pd.read_csv(file_path)
        row_count, col_count = df.shape

        columns = []
        quality_flags = []

        # Check duplicate rows
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            quality_flags.append({
                "type": "WARNING",
                "column": None,
                "message": f"{dup_count} duplicate rows detected",
            })

        for col in df.columns:
            series = df[col]
            null_count = int(series.isna().sum())
            null_pct = round(null_count / row_count * 100, 2) if row_count > 0 else 0.0

            # sample_values: first 3 non-null, stringified
            non_null = series.dropna()
            sample_values = [str(v) for v in non_null.head(3).tolist()]

            dtype_str = str(series.dtype)

            col_info: dict = {
                "name": col,
                "dtype": dtype_str,
                "null_count": null_count,
                "null_pct": null_pct,
                "sample_values": sample_values,
            }

            # Numeric stats
            if pd.api.types.is_numeric_dtype(series):
                desc = series.describe(percentiles=[0.25, 0.5, 0.75])
                col_info["stats"] = {
                    "min": _safe_float(desc.get("min")),
                    "max": _safe_float(desc.get("max")),
                    "mean": _safe_float(desc.get("mean")),
                    "std": _safe_float(desc.get("std")),
                    "p25": _safe_float(desc.get("25%")),
                    "p50": _safe_float(desc.get("50%")),
                    "p75": _safe_float(desc.get("75%")),
                }
            else:
                # Categorical: top-5 value_counts
                vc = series.value_counts().head(5)
                col_info["value_counts"] = {str(k): int(v) for k, v in vc.items()}

            columns.append(col_info)

            # Quality flags per column
            if null_count == row_count and row_count > 0:
                quality_flags.append({
                    "type": "ERROR",
                    "column": col,
                    "message": f"Column '{col}' is entirely null",
                })
            elif null_pct > 20:
                quality_flags.append({
                    "type": "WARNING",
                    "column": col,
                    "message": f"{null_count} null values ({null_pct}%)",
                })

        profile = {
            "row_count": row_count,
            "column_count": col_count,
            "columns": columns,
            "quality_flags": quality_flags,
        }

        updated_file = {**file_info, "profile_json": profile}
        updated_files = [updated_file] + files[1:]

        duration_ms = int((time.time() - t0) * 1000)
        log.info("node_exit", duration_ms=duration_ms, row_count=row_count)

        return {**state, "action": "profile", "uploaded_files": updated_files}

    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        log.error("node_error", error=str(exc), duration_ms=duration_ms)
        return {**state, "error": str(exc)}


def _safe_float(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        if np.isnan(f) or np.isinf(f):
            return None
        return round(f, 6)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# plan_and_code — calls Gemini to generate pandas code
# ---------------------------------------------------------------------------

def plan_and_code(state: AgentState) -> AgentState:
    """Generate pandas code to answer the user's question using Gemini."""
    t0 = time.time()
    session_id = state.get("session_id", "")
    log = logger.bind(node="plan_and_code", session_id=session_id)
    log.info("node_enter")

    try:
        question = state.get("current_question", "")
        uploaded_files = state.get("uploaded_files", [])

        # Build schema+stats context (NO raw row values)
        schema_parts = []
        for f in uploaded_files:
            fname = f["filename"]
            stem = Path(fname).stem
            profile = f.get("profile_json")
            if isinstance(profile, str):
                profile = json.loads(profile)

            if not profile:
                continue

            schema_parts.append(f"DataFrame '{stem}' (from '{fname}'):")
            schema_parts.append(f"  Rows: {profile.get('row_count', '?')}")
            schema_parts.append("  Columns:")
            for col in profile.get("columns", []):
                cname = col["name"]
                dtype = col["dtype"]
                null_count = col.get("null_count", 0)
                null_pct = col.get("null_pct", 0)

                if "stats" in col:
                    s = col["stats"]
                    schema_parts.append(
                        f"    - {cname} ({dtype}): "
                        f"min={s.get('min')}, max={s.get('max')}, "
                        f"mean={s.get('mean')}, std={s.get('std')}, "
                        f"p25={s.get('p25')}, p50={s.get('p50')}, p75={s.get('p75')}, "
                        f"nulls={null_count} ({null_pct}%)"
                    )
                elif "value_counts" in col:
                    vc = col["value_counts"]
                    vc_str = ", ".join(f"'{k}': {v}" for k, v in list(vc.items())[:5])
                    schema_parts.append(
                        f"    - {cname} ({dtype}): top values [{vc_str}], nulls={null_count} ({null_pct}%)"
                    )
                else:
                    schema_parts.append(f"    - {cname} ({dtype}): nulls={null_count} ({null_pct}%)")

        schema_context = "\n".join(schema_parts)

        # Conversation history from DB (last 20 messages)
        history_parts = []
        try:
            from db.session import create_db_session
            from db.models import MessageRow
            from sqlalchemy import select

            with create_db_session() as db:
                stmt = (
                    select(MessageRow)
                    .where(MessageRow.session_id == session_id)
                    .order_by(MessageRow.created_at.asc())
                    .limit(20)
                )
                messages = db.execute(stmt).scalars().all()
                for msg in messages:
                    history_parts.append(f"{msg.role.upper()}: {msg.content}")
        except Exception as hist_exc:
            log.warning("history_load_failed", error=str(hist_exc))

        history_context = "\n".join(history_parts) if history_parts else "(no prior conversation)"

        # File stems available
        stems = [Path(f["filename"]).stem for f in uploaded_files]

        system_prompt = _load_prompt(_CODE_GEN_PROMPT_PATH)

        prompt = f"""Available DataFrames in the `dfs` dict (keyed by filename stem): {stems}

{schema_context}

Conversation history (last 20 messages):
{history_context}

Current question: {question}

Generate Python code that answers the question.
- Access data via: dfs['{stems[0] if stems else "data"}']
- Store your final answer in a variable named `result`
- If a chart would help, store a Plotly figure in `fig`
- Do not use imports — pd, np, go, px are already available
- Do not print anything
"""

        generated_code = LLMClient().call_model(prompt, system=system_prompt)

        # Strip markdown code fences if present
        generated_code = _strip_code_fences(generated_code)

        duration_ms = int((time.time() - t0) * 1000)
        log.info("node_exit", duration_ms=duration_ms)

        return {**state, "generated_code": generated_code}

    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        log.error("node_error", error=str(exc), duration_ms=duration_ms)
        return {**state, "error": str(exc)}


def _strip_code_fences(code: str) -> str:
    """Remove markdown code fences (```python ... ```) if present."""
    lines = code.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# execute_code — run generated code in sandboxed exec()
# ---------------------------------------------------------------------------

def execute_code(state: AgentState) -> AgentState:
    """Execute the generated pandas code in a sandboxed namespace with 30s timeout."""
    t0 = time.time()
    session_id = state.get("session_id", "")
    log = logger.bind(node="execute_code", session_id=session_id)
    log.info("node_enter")

    try:
        code = state.get("generated_code", "")
        uploaded_files = state.get("uploaded_files", [])

        # Load all uploaded CSVs as DataFrames
        dfs_dict: dict = {}
        for f in uploaded_files:
            stem = Path(f["filename"]).stem
            fpath = f.get("path") or f.get("temp_path")
            if fpath and Path(fpath).exists():
                dfs_dict[stem] = pd.read_csv(fpath)
            else:
                log.warning("file_not_found", filename=f["filename"])

        namespace = {
            "dfs": dfs_dict,
            "pd": pd,
            "np": np,
            "go": go,
            "px": px,
        }

        exec_result = _exec_with_timeout(code, namespace, _EXEC_TIMEOUT_SECONDS)

        if exec_result["timed_out"]:
            return {**state, "error": f"Code execution timed out after {_EXEC_TIMEOUT_SECONDS} seconds"}

        if exec_result["error"]:
            return {**state, "error": exec_result["error"]}

        result_val = namespace.get("result")
        fig_val = namespace.get("fig")

        execution_result = str(result_val) if result_val is not None else "No result produced"

        chart_json = None
        if fig_val is not None:
            try:
                chart_json = json.loads(fig_val.to_json())
            except Exception as fig_exc:
                log.warning("chart_serialize_failed", error=str(fig_exc))

        duration_ms = int((time.time() - t0) * 1000)
        log.info("node_exit", duration_ms=duration_ms, has_chart=chart_json is not None)

        return {**state, "execution_result": execution_result, "chart_json": chart_json}

    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        log.error("node_error", error=str(exc), duration_ms=duration_ms)
        return {**state, "error": str(exc)}


def _exec_with_timeout(code: str, namespace: dict, timeout: float) -> dict:
    """Execute code in a thread with timeout. Returns {timed_out, error}."""
    result: dict = {"timed_out": False, "error": None}

    def _run():
        try:
            exec(code, namespace)  # noqa: S102
        except Exception:
            result["error"] = traceback.format_exc(limit=5)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run)
        try:
            future.result(timeout=timeout)
        except FuturesTimeoutError:
            result["timed_out"] = True

    return result


# ---------------------------------------------------------------------------
# format_response — call Gemini to write prose answer
# ---------------------------------------------------------------------------

def format_response(state: AgentState) -> AgentState:
    """Convert execution_result to a clear prose answer using Gemini."""
    t0 = time.time()
    session_id = state.get("session_id", "")
    log = logger.bind(node="format_response", session_id=session_id)
    log.info("node_enter")

    try:
        question = state.get("current_question", "")
        execution_result = state.get("execution_result", "")

        system_prompt = _load_prompt(_FORMAT_PROMPT_PATH)

        prompt = (
            f"The user asked: {question}\n\n"
            f"The computation returned: {execution_result}\n\n"
            "Write a clear, concise answer for a non-technical reader in 2-3 sentences."
        )

        answer = LLMClient().call_model(prompt, system=system_prompt)

        duration_ms = int((time.time() - t0) * 1000)
        log.info("node_exit", duration_ms=duration_ms)

        return {**state, "answer": answer}

    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        log.error("node_error", error=str(exc), duration_ms=duration_ms)
        return {**state, "error": str(exc)}


# ---------------------------------------------------------------------------
# handle_error — produce a user-friendly error message
# ---------------------------------------------------------------------------

def handle_error(state: AgentState) -> AgentState:
    """Return a user-friendly error message."""
    error = state.get("error", "unknown error")
    logger.bind(node="handle_error", session_id=state.get("session_id", "")).warning(
        "error_handled", error=error
    )
    return {
        **state,
        "action": "error",
        "answer": f"I encountered an error: {error}. Please try rephrasing your question.",
    }
