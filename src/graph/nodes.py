"""LangGraph nodes for the text-to-SQL data-analyst flow.

Token economy is central: the LLM only ever sees the cached schema, a ≤20-row
sample, and (for the answer) the small result set — NEVER full dataset rows.
"""
import json
import re
import time
from pathlib import Path

from db.models import AuditLogEntry
from db.session import create_db_session, _get_engine
from graph.state import AgentState
from llm.client import LLMClient
from sql.sandbox import SandboxViolation, execute_select

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

# Cap the result rows fed back to the answer LLM (already small; safety bound).
_ANSWER_ROW_CAP = 200


def _load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def _strip_fences(text: str) -> str:
    """Strip markdown code fences the model may emit around SQL."""
    t = text.strip()
    fence = re.match(r"^```[a-zA-Z]*\s*(.*?)\s*```$", t, flags=re.DOTALL)
    if fence:
        t = fence.group(1).strip()
    return t.strip()


def build_sql_prompt(state: AgentState) -> str:
    """The bounded user prompt for generate_sql — schema + sample + question only."""
    return (
        f"Table name: {state['table_name']}\n\n"
        f"Schema:\n{state.get('schema_text', '')}\n\n"
        f"Sample rows (at most 20):\n{state.get('sample_text', '')}\n\n"
        f"Question: {state['question']}\n\n"
        f"Write one read-only SELECT over {state['table_name']} that answers it."
    )


def generate_sql(state: AgentState) -> AgentState:
    try:
        system = _load_prompt("text_to_sql.md")
        prompt = build_sql_prompt(state)
        raw = LLMClient().call_model(prompt, system=system)
        if not raw or not raw.strip():
            return {**state, "error": "LLM returned empty SQL"}
        sql = _strip_fences(raw)
        return {**state, "generated_sql": sql}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"SQL generation failed: {exc}"}


def _write_query_audit(
    state: AgentState,
    *,
    sql_text: str,
    row_count,
    columns,
    duration_ms: int,
    success: bool,
    error_message: str | None,
) -> None:
    try:
        with create_db_session() as session:
            session.add(
                AuditLogEntry(
                    operation="query",
                    dataset_id=state.get("dataset_id"),
                    query_id=state.get("query_id"),
                    sql_text=sql_text,
                    row_count=row_count,
                    columns_json=json.dumps(columns) if columns is not None else None,
                    duration_ms=duration_ms,
                    success=success,
                    error_message=error_message,
                )
            )
    except Exception:  # noqa: BLE001 - audit write failure must not crash the run
        pass


def execute_sql(state: AgentState) -> AgentState:
    sql = state.get("generated_sql", "")
    table_name = state["table_name"]
    start = time.perf_counter()
    raw_conn = _get_engine().raw_connection()
    try:
        result = execute_select(raw_conn, sql, [table_name])
        duration_ms = result["duration_ms"]
        _write_query_audit(
            state,
            sql_text=result["sql"],
            row_count=result["row_count"],
            columns=result["columns"],
            duration_ms=duration_ms,
            success=True,
            error_message=None,
        )
        return {
            **state,
            "result_columns": result["columns"],
            "result_rows": result["rows"],
            "row_count": result["row_count"],
            "duration_ms": duration_ms,
        }
    except SandboxViolation as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        msg = f"SQL rejected by sandbox: {exc}"
        _write_query_audit(
            state, sql_text=sql, row_count=None, columns=None,
            duration_ms=duration_ms, success=False, error_message=msg,
        )
        return {**state, "error": msg}
    except Exception as exc:  # noqa: BLE001 - SQL execution error
        duration_ms = int((time.perf_counter() - start) * 1000)
        msg = f"SQL execution failed: {exc}"
        _write_query_audit(
            state, sql_text=sql, row_count=None, columns=None,
            duration_ms=duration_ms, success=False, error_message=msg,
        )
        return {**state, "error": msg}
    finally:
        raw_conn.close()


def _build_answer_prompt(state: AgentState) -> str:
    columns = state.get("result_columns", [])
    rows = state.get("result_rows", [])[:_ANSWER_ROW_CAP]
    return (
        f"Question: {state['question']}\n\n"
        f"Result columns: {json.dumps(columns)}\n"
        f"Result rows ({state.get('row_count', len(rows))} total, "
        f"showing up to {_ANSWER_ROW_CAP}):\n{json.dumps(rows, default=str)}"
    )


def compose_answer(state: AgentState) -> AgentState:
    try:
        system = _load_prompt("answer.md")
        prompt = _build_answer_prompt(state)
        answer = LLMClient().call_model(prompt, system=system)
        if not answer or not answer.strip():
            return {**state, "error": "LLM returned empty answer"}
        return {**state, "answer_text": answer.strip()}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"Answer composition failed: {exc}"}


def finalize(state: AgentState) -> AgentState:
    return {**state, "status": "completed"}


def handle_error(state: AgentState) -> AgentState:
    return {**state, "status": "failed"}
