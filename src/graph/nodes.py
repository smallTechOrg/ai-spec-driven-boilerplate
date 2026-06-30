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
_CLARIFY_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "clarify.md"
_REFLECT_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "reflect.md"

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
        filename = file_info["filename"]

        if filename.lower().endswith(".xlsx"):
            df = pd.read_excel(file_path, engine="openpyxl")
        else:
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
# needs_clarification — determine if the question is ambiguous before coding
# ---------------------------------------------------------------------------

def needs_clarification(state: AgentState) -> AgentState:
    """Determine if the user's question needs clarification before code generation."""
    t0 = time.time()
    session_id = state.get("session_id", "")
    log = logger.bind(node="needs_clarification", session_id=session_id)
    log.info("node_enter")

    try:
        question = state.get("current_question", "")
        uploaded_files = state.get("uploaded_files", [])

        # Build column list from schema (no raw rows)
        col_parts = []
        for f in uploaded_files:
            fname = f["filename"]
            stem = Path(fname).stem
            profile = f.get("profile_json")
            if isinstance(profile, str):
                import json as _json
                profile = _json.loads(profile)
            if profile:
                cols = [c["name"] for c in profile.get("columns", [])]
                col_parts.append(f"DataFrame '{stem}': columns = {cols}")

        schema_summary = "\n".join(col_parts) if col_parts else "No files uploaded."

        # Load conversation history for context
        history_parts = []
        try:
            from db.session import create_db_session
            from db.models import MessageRow
            from sqlalchemy import select as sa_select
            with create_db_session() as db:
                stmt = (
                    sa_select(MessageRow)
                    .where(MessageRow.session_id == session_id)
                    .order_by(MessageRow.created_at.asc())
                    .limit(10)
                )
                messages = db.execute(stmt).scalars().all()
                for msg in messages:
                    history_parts.append(f"{msg.role.upper()}: {msg.content}")
        except Exception as hist_exc:
            log.warning("history_load_failed", error=str(hist_exc))

        history_context = "\n".join(history_parts) if history_parts else "(no prior conversation)"

        system_prompt = _load_prompt(_CLARIFY_PROMPT_PATH)

        prompt = f"""Schema (column names only — no raw data):
{schema_summary}

Recent conversation:
{history_context}

User question: {question}

Your default is PROCEED. A skilled data analyst almost never needs to ask a follow-up question.

ALWAYS respond PROCEED for these patterns (make a sensible default choice):
- "Compare X vs Y" or "Compare cancelled vs non-cancelled" → filter/group on the obvious column and compare all numeric columns
- "Summarize the dataset" or "Overview" or "Explore" → compute summary stats for all columns
- "Show top customers / products / regions / categories" → group by the obvious dimension, aggregate, show top 10
- "Show the trend" or "Plot over time" → use the date/time column and the most prominent numeric column
- "What is the distribution of X?" → histogram or value counts of that column
- "Average / total / count of X" → compute that aggregation
- Any question where a reasonable default exists, even if multiple columns could qualify

ONLY respond CLARIFICATION_NEEDED when ALL of these are true:
1. You genuinely cannot make a reasonable default choice (e.g. "plot it" with no prior context and multiple equally plausible columns AND no date column)
2. The conversation history does not resolve the ambiguity
3. Without the answer, you would produce a completely useless or misleading result

If a pronoun like "it" or "that" resolves from the last 1–2 turns of conversation history, respond PROCEED.

If TRULY AMBIGUOUS (meets all 3 conditions above): respond with exactly:
CLARIFICATION_NEEDED: <one short clarifying question>

Otherwise: respond with exactly:
PROCEED

Do not add any other text."""

        response = LLMClient().call_model(prompt, system=system_prompt)
        response = response.strip()

        duration_ms = int((time.time() - t0) * 1000)

        if response.startswith("CLARIFICATION_NEEDED:"):
            clarification_question = response[len("CLARIFICATION_NEEDED:"):].strip()
            log.info("node_exit_clarification", duration_ms=duration_ms)
            return {**state, "action": "clarification", "answer": clarification_question}
        else:
            log.info("node_exit_proceed", duration_ms=duration_ms)
            return {**state}

    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        log.error("node_error", error=str(exc), duration_ms=duration_ms)
        # On any error in clarification check, proceed normally rather than blocking
        return {**state}


# ---------------------------------------------------------------------------
# inspect_quality — deterministic pandas-only data quality check + auto-clean
# ---------------------------------------------------------------------------

def inspect_quality(state: AgentState) -> AgentState:
    """Inspect uploaded files for data quality issues and apply safe auto-fixes.

    Purely deterministic — NO LLM call. Runs before plan_and_code.
    Auto-fixes: duplicate row removal, numeric string coercion.
    Reports (no fix): missing values, invalid dates, outliers.
    Overwrites the temp file in place so execute_code reads cleaned data.
    """
    t0 = time.time()
    session_id = state.get("session_id", "")
    log = logger.bind(node="inspect_quality", session_id=session_id)
    log.info("node_enter")

    try:
        files = state.get("uploaded_files", [])
        if not files:
            return {**state, "quality_report": {"has_issues": False, "files": [], "clean_actions": []}, "clean_actions": []}

        all_file_reports = []
        all_clean_actions: list[str] = []

        updated_files = list(files)  # shallow copy; we'll replace entries

        for idx, file_info in enumerate(files):
            filename = file_info.get("filename", "")
            file_path = file_info.get("path") or file_info.get("temp_path")

            if not file_path or not Path(file_path).exists():
                log.warning("file_not_found", filename=filename)
                continue

            try:
                if filename.lower().endswith(".xlsx"):
                    df = pd.read_excel(file_path, engine="openpyxl")
                else:
                    df = pd.read_csv(file_path)
            except Exception as read_exc:
                log.warning("file_read_failed", filename=filename, error=str(read_exc))
                continue

            file_issues: list[dict] = []
            dup_rows_removed = 0
            file_clean_actions: list[str] = []
            row_count = len(df)

            # 1. DUPLICATE ROWS
            dup_count = int(df.duplicated().sum())
            if dup_count > 0:
                df = df.drop_duplicates()
                dup_rows_removed = dup_count
                msg = f"Removed {dup_count} duplicate rows from '{filename}'"
                file_clean_actions.append(msg)
                all_clean_actions.append(msg)

            # 2. MISSING VALUES — report only
            for col in df.columns:
                null_count = int(df[col].isna().sum())
                if null_count > 0 and row_count > 0:
                    null_pct = round(null_count / row_count * 100, 2)
                    file_issues.append({
                        "type": "WARNING",
                        "category": "missing_values",
                        "column": col,
                        "detail": f"{null_count} missing values ({null_pct}%)",
                    })

            # 3. TYPE MISMATCH — numeric strings: auto-coerce if 100% convertible and >= 3 non-null
            for col in df.columns:
                is_str_col = (
                    pd.api.types.is_string_dtype(df[col])
                    or pd.api.types.is_object_dtype(df[col])
                ) and not pd.api.types.is_numeric_dtype(df[col])
                if is_str_col:
                    non_null = df[col].dropna()
                    if len(non_null) >= 3:
                        coerced = pd.to_numeric(non_null, errors="coerce")
                        if coerced.notna().all():
                            df[col] = pd.to_numeric(df[col], errors="coerce")
                            msg = f"Coerced column '{col}' in '{filename}' from text to numeric"
                            file_clean_actions.append(msg)
                            all_clean_actions.append(msg)
                            file_issues.append({
                                "type": "INFO",
                                "category": "type_mismatch",
                                "column": col,
                                "detail": "Stored as text but all values are numeric — coerced automatically",
                            })

            # 4. INVALID DATES — report only (no auto-fix)
            date_keywords = ["date", "time", "dt", "_at", "_on"]
            for col in df.columns:
                is_str_col = (
                    pd.api.types.is_string_dtype(df[col])
                    or pd.api.types.is_object_dtype(df[col])
                ) and not pd.api.types.is_numeric_dtype(df[col])
                if is_str_col:
                    col_lower = col.lower()
                    if any(kw in col_lower for kw in date_keywords):
                        non_null = df[col].dropna()
                        if len(non_null) > 0:
                            try:
                                parsed = pd.to_datetime(non_null, errors="coerce")
                                nat_count = int(parsed.isna().sum())
                                if nat_count > 0:
                                    file_issues.append({
                                        "type": "WARNING",
                                        "category": "invalid_dates",
                                        "column": col,
                                        "detail": f"{nat_count} values could not be parsed as dates",
                                    })
                            except Exception:
                                pass

            # 5. OUTLIERS — IQR (Tukey) method: robust against extreme skew, report only (no auto-fix)
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_data = df[col].dropna()
                    if len(col_data) >= 4:
                        q1 = col_data.quantile(0.25)
                        q3 = col_data.quantile(0.75)
                        iqr = q3 - q1
                        if iqr > 0:
                            lower_fence = q1 - 1.5 * iqr
                            upper_fence = q3 + 1.5 * iqr
                            outlier_count = int(
                                ((col_data < lower_fence) | (col_data > upper_fence)).sum()
                            )
                            if outlier_count > 0:
                                file_issues.append({
                                    "type": "INFO",
                                    "category": "outliers",
                                    "column": col,
                                    "detail": f"{outlier_count} values beyond 1.5x IQR (potential outliers)",
                                })

            # Write cleaned DataFrame back to same path (overwrite)
            try:
                if filename.lower().endswith(".xlsx"):
                    df.to_excel(file_path, index=False, engine="openpyxl")
                else:
                    df.to_csv(file_path, index=False)
            except Exception as write_exc:
                log.warning("file_write_failed", filename=filename, error=str(write_exc))

            # Update the file entry (path unchanged, but record clean actions)
            updated_files[idx] = {**file_info}

            has_file_issues = len(file_issues) > 0 or dup_rows_removed > 0
            all_file_reports.append({
                "filename": filename,
                "issues": file_issues,
                "duplicate_rows_removed": dup_rows_removed,
            })

        has_issues = len(all_clean_actions) > 0 or any(
            r["issues"] for r in all_file_reports
        )

        if not has_issues and not all_file_reports:
            quality_report = {"has_issues": False, "files": [], "clean_actions": []}
        else:
            quality_report = {
                "has_issues": has_issues,
                "files": all_file_reports,
                "clean_actions": all_clean_actions,
            }

        duration_ms = int((time.time() - t0) * 1000)
        log.info(
            "node_exit",
            duration_ms=duration_ms,
            has_issues=has_issues,
            clean_actions_count=len(all_clean_actions),
        )

        return {
            **state,
            "uploaded_files": updated_files,
            "quality_report": quality_report,
            "clean_actions": all_clean_actions,
        }

    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        log.error("node_error", error=str(exc), duration_ms=duration_ms)
        # Graceful degradation: return state unchanged so Q&A can still proceed
        return {**state}


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

        # Append clean_actions note if any auto-cleaning was applied
        clean_actions = state.get("clean_actions") or []
        if clean_actions:
            clean_note_lines = [
                "",
                "Note: The following data cleaning was applied automatically before this query:",
            ]
            for action in clean_actions:
                clean_note_lines.append(f"- {action}")
            schema_context += "\n" + "\n".join(clean_note_lines)

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


_MAX_RESULT_ROWS = 200
_MAX_RESULT_CHARS = 4000


def _serialize_result(result_val) -> str:
    """Convert exec() result to a string suitable for the format LLM."""
    if result_val is None:
        return "No result produced"
    if isinstance(result_val, pd.DataFrame):
        if result_val.empty:
            return "Query returned an empty table."
        rows = min(len(result_val), _MAX_RESULT_ROWS)
        snippet = result_val.head(rows).to_string(index=False)
        suffix = f"\n[Showing {rows} of {len(result_val)} rows]" if len(result_val) > rows else ""
        return snippet + suffix
    if isinstance(result_val, pd.Series):
        rows = min(len(result_val), _MAX_RESULT_ROWS)
        snippet = result_val.head(rows).to_string()
        suffix = f"\n[Showing {rows} of {len(result_val)} entries]" if len(result_val) > rows else ""
        return snippet + suffix
    # numpy scalars → Python native
    if hasattr(result_val, "item"):
        try:
            result_val = result_val.item()
        except Exception:
            pass
    text = str(result_val)
    if len(text) > _MAX_RESULT_CHARS:
        text = text[:_MAX_RESULT_CHARS] + "\n[truncated]"
    return text


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

        # Load all uploaded files as DataFrames (CSV or Excel)
        dfs_dict: dict = {}
        for f in uploaded_files:
            stem = Path(f["filename"]).stem
            fpath = f.get("path") or f.get("temp_path")
            if fpath and Path(fpath).exists():
                if f["filename"].lower().endswith(".xlsx"):
                    dfs_dict[stem] = pd.read_excel(fpath, engine="openpyxl")
                else:
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
            return {**state, "error": f"Code execution timed out after {_EXEC_TIMEOUT_SECONDS}s. Try a simpler question or a smaller slice of the data."}

        if exec_result["error"]:
            exc_type = exec_result.get("exc_type", "Error")
            exc_msg = exec_result["error"]
            available_cols = ", ".join(
                f'"{c["name"]}"' for f in (state.get("uploaded_files") or [])
                for c in (f.get("profile_json") or {}).get("columns", [])
            ) if state.get("uploaded_files") else ""
            col_hint = f" Available columns: {available_cols}." if available_cols and exc_type in ("KeyError", "AttributeError", "ValueError") else ""
            return {**state, "error": f"{exc_type}: {exc_msg}.{col_hint}"}

        result_val = namespace.get("result")
        fig_val = namespace.get("fig")

        execution_result = _serialize_result(result_val)

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
    """Execute code in a thread with timeout. Returns {timed_out, error, exc_type}."""
    result: dict = {"timed_out": False, "error": None, "exc_type": None}

    def _run():
        try:
            exec(code, namespace)  # noqa: S102
        except Exception as exc:
            result["exc_type"] = type(exc).__name__
            result["error"] = str(exc)

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

        # Truncate the result if it's enormous to avoid hitting token limits
        result_for_llm = execution_result
        if len(result_for_llm) > _MAX_RESULT_CHARS:
            result_for_llm = result_for_llm[:_MAX_RESULT_CHARS] + "\n[result truncated for brevity]"

        prompt = (
            f"The user asked: {question}\n\n"
            f"The computation returned:\n{result_for_llm}\n\n"
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
# reflect_and_retry — reflect on failed code and generate a corrected version
# ---------------------------------------------------------------------------

def reflect_and_retry(state: AgentState) -> AgentState:
    """Reflect on failed code and generate a corrected version."""
    t0 = time.time()
    session_id = state.get("session_id", "")
    log = logger.bind(node="reflect_and_retry", session_id=session_id)
    retry_count = state.get("retry_count", 0)
    log.info("node_enter", retry_count=retry_count)

    try:
        question = state.get("current_question", "")
        failed_code = state.get("generated_code", "")
        error_msg = state.get("error", "Unknown error")
        uploaded_files = state.get("uploaded_files", [])

        # Build schema context
        schema_parts = []
        for f in uploaded_files:
            import json as _json
            fname = f["filename"]
            stem = Path(fname).stem
            profile = f.get("profile_json")
            if isinstance(profile, str):
                profile = _json.loads(profile)
            if profile:
                cols = [f"  - {c['name']} ({c['dtype']})" for c in profile.get("columns", [])]
                schema_parts.append(f"DataFrame '{stem}':\n" + "\n".join(cols))

        schema_context = "\n".join(schema_parts) if schema_parts else "No schema available."
        stems = [Path(f["filename"]).stem for f in uploaded_files]

        system_prompt = _load_prompt(_REFLECT_PROMPT_PATH)

        prompt = f"""The user asked: {question}

Available DataFrames in `dfs` dict (keyed by filename stem): {stems}

Schema:
{schema_context}

The following code was generated but failed with an error:

--- FAILED CODE ---
{failed_code}
--- END CODE ---

Error message:
{error_msg}

Please generate corrected Python code that:
1. Fixes the error
2. Still answers the original question
3. Uses the same conventions: access data via dfs['{stems[0] if stems else "data"}'], store final answer in `result`, optional chart in `fig`
4. Does NOT use imports — pd, np, go, px are already available
5. Does NOT print anything

Return ONLY the corrected Python code, no explanation, no markdown fences."""

        corrected_code = LLMClient().call_model(prompt, system=system_prompt)
        corrected_code = _strip_code_fences(corrected_code)

        duration_ms = int((time.time() - t0) * 1000)
        log.info("node_exit", duration_ms=duration_ms, new_retry_count=retry_count + 1)

        return {
            **state,
            "generated_code": corrected_code,
            "error": None,
            "retry_count": retry_count + 1,
        }

    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        log.error("node_error", error=str(exc), duration_ms=duration_ms)
        # Reflection itself failed — keep the original error so handle_error sees it
        return {**state}


# ---------------------------------------------------------------------------
# handle_error — produce a user-friendly error message
# ---------------------------------------------------------------------------

def handle_error(state: AgentState) -> AgentState:
    """Return a user-friendly error message without exposing Python internals."""
    error = state.get("error", "unknown error")
    logger.bind(node="handle_error", session_id=state.get("session_id", "")).warning(
        "error_handled", error=error
    )
    # Build a helpful, non-technical message
    msg = _user_friendly_error(error)
    return {
        **state,
        "action": "error",
        "answer": msg,
    }


def _user_friendly_error(error: str) -> str:
    """Map internal error strings to helpful user-facing messages."""
    e = error.lower()
    if "timed out" in e:
        return "That question took too long to compute. Try asking for a smaller subset of the data or a simpler calculation."
    if "keyerror" in e or "column" in e:
        return f"I couldn't find a column needed to answer that question. {error.split('.')[0] if '.' in error else error} — please check the column names in the profile card and try again."
    if "no result produced" in e:
        return "The generated code ran but didn't produce a value. Try rephrasing the question to be more specific (e.g. 'What is the sum of revenue?' instead of 'Revenue')."
    if "empty" in e:
        return "The query returned no matching rows. Try relaxing your filter conditions."
    if "valueerror" in e or "typeerror" in e:
        return f"There was a data type issue computing the answer: {error.split('.')[0] if '.' in error else error}. Try specifying the column name explicitly."
    if "syntaxerror" in e:
        return "I had trouble generating valid code for that question. Could you rephrase it more specifically?"
    if "no llm provider" in e or "api_key" in e.replace("-", "_"):
        return "The AI service is not configured. Please check that an API key is set in .env."
    if "quota" in e or "rate" in e or "429" in e:
        return "The AI service is temporarily rate-limited. Please wait a moment and try again."
    if "timeout" in e or "deadline" in e:
        return "The AI service took too long to respond. Please try again."
    # Generic fallback — show error type but not Python internals
    first_line = error.strip().split("\n")[0][:200]
    return f"I wasn't able to answer that question ({first_line}). Please try rephrasing or ask a more specific question."
