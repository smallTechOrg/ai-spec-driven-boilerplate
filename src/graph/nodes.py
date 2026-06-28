"""LangGraph nodes for the Data Analysis Agent pipeline."""

from __future__ import annotations

import ast
import json
import re
import time
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from graph.state import AgentState

log = structlog.get_logger("agent.nodes")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLAN_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "plan_analysis.md"
_REASON_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "reason_answer.md"

_FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "socket", "requests", "urllib"}

_SANDBOX_WHITELIST = {
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "sorted": sorted,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "bool": bool,
    "print": print,
}


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _extract_json(text: str) -> dict:
    """Strip markdown code fences then parse JSON."""
    text = text.strip()
    # Remove leading ```json or ```
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    # Remove trailing ```
    text = re.sub(r"\n?```\s*$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(text.strip())


def _gemini_call(model: str, system_prompt: str, user_message: str, *, retries: int = 2) -> str:
    """Call the Gemini API directly with retry logic."""
    from google import genai
    from google.genai import types
    from config.settings import get_settings

    s = get_settings()
    client = genai.Client(api_key=s.gemini_api_key)

    config = types.GenerateContentConfig(system_instruction=system_prompt)

    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            t0 = time.monotonic()
            response = client.models.generate_content(
                model=model,
                contents=user_message,
                config=config,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            log.info("llm_call", model=model, latency_ms=latency_ms)
            return response.text
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                wait = 2 ** attempt  # 1s, 2s
                time.sleep(wait)
    raise last_exc  # type: ignore[misc]


def _check_forbidden_imports(code: str) -> None:
    """Raise ValueError if the code uses forbidden imports."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            else:
                names = [node.module.split(".")[0]] if node.module else []
            for name in names:
                if name in _FORBIDDEN_IMPORTS:
                    raise ValueError(f"Forbidden import: {name!r}")
        # Also block open() and exec() calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("open", "exec", "eval", "__import__"):
                raise ValueError(f"Forbidden call: {node.func.id}()")


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def load_dataset(state: AgentState) -> AgentState:
    """Load the uploaded file from disk into a DataFrame."""
    try:
        from db.session import create_db_session
        from db.models import UploadedFile
        from sqlalchemy import select

        file_id = state["file_id"]

        with create_db_session() as session:
            file_row = session.get(UploadedFile, file_id)
            if file_row is None:
                raise ValueError(f"File record not found in DB: {file_id!r}")
            file_path = file_row.file_path
            source_type = file_row.source_type or "csv"

        if not file_path or not Path(file_path).exists():
            raise FileNotFoundError(f"File not found on disk: {file_path!r}")

        if source_type == "csv":
            df = pd.read_csv(file_path)
        elif source_type in ("excel", "xlsx", "xls"):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        head3 = df.head(3)
        schema_info: dict = {
            "columns": list(df.columns),
            "dtypes": df.dtypes.apply(str).to_dict(),
            "sample_rows": head3.where(pd.notnull(head3), None).values.tolist(),
        }

        log.info("load_dataset", file_id=file_id, rows=len(df), columns=len(df.columns))
        return {**state, "df": df, "schema_info": schema_info, "file_path": file_path, "source_type": source_type}

    except Exception as exc:  # noqa: BLE001
        log.error("load_dataset_failed", error=str(exc))
        return {**state, "error": str(exc)}


def plan_analysis(state: AgentState) -> AgentState:
    """Call the LLM to generate Pandas code for the user's question."""
    try:
        schema_info = state.get("schema_info", {})
        question = state.get("question", "")
        system_prompt = _load_prompt(_PLAN_PROMPT_PATH)

        user_message = (
            f"Schema:\n{json.dumps(schema_info, indent=2)}\n\n"
            f"Question: {question}"
        )

        from config.settings import get_settings
        s = get_settings()
        model = s.llm_model_plan or "gemini-2.5-flash"

        raw = _gemini_call(model, system_prompt, user_message)
        parsed = _extract_json(raw)

        code_type = str(parsed.get("code_type", "pandas"))
        code = str(parsed.get("code", ""))

        if not code:
            raise ValueError("LLM returned empty code")

        _check_forbidden_imports(code)

        log.info("plan_analysis", code_type=code_type, code_length=len(code))
        return {**state, "generated_code": code, "code_type": code_type}

    except Exception as exc:  # noqa: BLE001
        log.error("plan_analysis_failed", error=str(exc))
        return {**state, "error": str(exc)}


def _exec_code_in_sandbox(code: str, df: "pd.DataFrame") -> str:
    """Execute code in restricted globals, return result_sample string."""
    restricted_globals: dict = {
        "df": df,
        "pd": pd,
        "__builtins__": _SANDBOX_WHITELIST,
    }
    exec(code, restricted_globals)  # noqa: S102

    result = restricted_globals.get("result")
    if result is None:
        raise ValueError("Code did not assign a value to 'result'")

    if isinstance(result, pd.DataFrame):
        return result.head(500).to_csv(index=False)
    return str(result)


def execute_code(state: AgentState) -> AgentState:
    """Execute the LLM-generated code in a sandboxed environment."""
    try:
        df = state.get("df")
        if df is None:
            raise ValueError("No DataFrame in state")

        code = state.get("generated_code", "")
        if not code:
            raise ValueError("No generated_code in state")

        t0 = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_exec_code_in_sandbox, code, df)
            try:
                result_sample = future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                raise TimeoutError("Code execution timed out after 30 seconds")

        latency_ms = int((time.monotonic() - t0) * 1000)
        result_rows = result_sample.count("\n") if result_sample else 0
        log.info("code_exec", result_rows=result_rows, latency_ms=latency_ms)

        return {**state, "result_sample": result_sample}

    except Exception as exc:  # noqa: BLE001
        log.error("execute_code_failed", error=str(exc))
        return {**state, "error": f"Code execution failed: {exc}"}


def reason_answer(state: AgentState) -> AgentState:
    """Call the LLM to produce a plain-English answer and a Plotly chart spec."""
    try:
        question = state.get("question", "")
        result_sample = state.get("result_sample", "")
        schema_info = state.get("schema_info", {})
        dtypes = schema_info.get("dtypes", {})

        system_prompt = _load_prompt(_REASON_PROMPT_PATH)
        user_message = (
            f"Question: {question}\n\n"
            f"Column dtypes: {json.dumps(dtypes)}\n\n"
            f"Result data (CSV):\n{result_sample}"
        )

        from config.settings import get_settings
        s = get_settings()
        model = s.llm_model_reason or "gemini-2.5-pro"

        raw = _gemini_call(model, system_prompt, user_message)
        parsed = _extract_json(raw)

        answer_text = str(parsed.get("answer_text", ""))
        chart_spec = parsed.get("chart_spec")

        # Validate chart_spec structure if present
        if chart_spec is not None:
            if not isinstance(chart_spec, dict):
                raise ValueError("chart_spec must be a dict or null")
            if "data" not in chart_spec or not isinstance(chart_spec["data"], list):
                raise ValueError("chart_spec.data must be a list")
            if "layout" not in chart_spec or not isinstance(chart_spec["layout"], dict):
                raise ValueError("chart_spec.layout must be a dict")

        log.info("reason_answer", answer_length=len(answer_text), has_chart=chart_spec is not None)
        return {**state, "answer_text": answer_text, "chart_spec": chart_spec}

    except Exception as exc:  # noqa: BLE001
        log.error("reason_answer_failed", error=str(exc))
        return {**state, "error": str(exc)}


def handle_error(state: AgentState) -> AgentState:
    """Log the error and persist the failed run record. Never raises."""
    try:
        run_id = state.get("run_id", "unknown")
        error = state.get("error", "unknown error")

        log.error("run_failed", run_id=run_id, error=error)

        # Attempt to update the AnalysisRun record in DB — best effort
        _persist_failed_run(state, error)

    except Exception as exc:  # noqa: BLE001
        # Never raise from handle_error
        log.error("handle_error_itself_failed", error=str(exc))

    return {**state, "status": "failed"}


def _persist_failed_run(state: AgentState, error: str) -> None:
    """Best-effort DB write for failed runs."""
    from db.session import create_db_session
    from db.models import AnalysisRun

    run_id = state.get("run_id")
    file_id = state.get("file_id")
    question = state.get("question", "")

    if not run_id:
        return

    with create_db_session() as session:
        run = session.get(AnalysisRun, run_id)
        if run is None and file_id:
            # Create the row if it doesn't exist yet
            run = AnalysisRun(
                id=run_id,
                file_id=file_id,
                question=question,
                status="failed",
                error_message=error,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(run)
        elif run is not None:
            run.status = "failed"
            run.error_message = error
            run.completed_at = datetime.now(timezone.utc)


def finalize(state: AgentState) -> AgentState:
    """Persist the completed analysis run and log the run summary."""
    try:
        from db.session import create_db_session
        from db.models import AnalysisRun

        run_id = state.get("run_id")
        file_id = state.get("file_id")
        question = state.get("question", "")
        answer_text = state.get("answer_text", "")
        chart_spec = state.get("chart_spec")
        chart_spec_json = json.dumps(chart_spec) if chart_spec is not None else None

        with create_db_session() as session:
            run = session.get(AnalysisRun, run_id) if run_id else None
            if run is None and file_id and run_id:
                run = AnalysisRun(
                    id=run_id,
                    file_id=file_id,
                    question=question,
                    answer_text=answer_text,
                    chart_spec_json=chart_spec_json,
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
                session.add(run)
            elif run is not None:
                run.answer_text = answer_text
                run.chart_spec_json = chart_spec_json
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)

        log.info("run_end", run_id=run_id, status="completed")

    except Exception as exc:  # noqa: BLE001
        log.error("finalize_failed", error=str(exc))
        return {**state, "status": "failed", "error": str(exc)}

    return {**state, "status": "completed"}
