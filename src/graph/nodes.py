"""Agent graph nodes for conversational data analysis.

Privacy invariant: every LLM call here is given ONLY the privacy-safe profile
(schema/stats/<=5-row sample built by src/analysis/profile.py), the user's
question/turns, generated code, errors, and a truncated/aggregated result
preview. No node ever passes a full DataFrame or bulk raw rows to the LLM.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from analysis.execute import execute_pandas
from analysis.profile import load_csv
from graph.state import AgentState
from llm.client import LLMClient
from observability.events import get_logger

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"
_log = get_logger("graph")

# Cap on prior conversation turns folded into context (sliding window).
_HISTORY_WINDOW = 8


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def _profile_text(profile: dict) -> str:
    """Render the privacy-safe profile for an LLM prompt. Sample is already
    capped at MAX_SAMPLE_ROWS by the profiler — this only formats it."""
    return json.dumps(profile, indent=2, default=str)


def _history_text(history: list) -> str:
    if not history:
        return "(no prior turns)"
    turns = history[-_HISTORY_WINDOW:]
    return "\n".join(f"{t.get('role', '?')}: {t.get('content', '')}" for t in turns)


def _extract_code(text: str) -> str:
    """Pull the python snippet out of a fenced block; fall back to raw text."""
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def _parse_verdict(text: str) -> str:
    """Parse the inspect verdict JSON; default to 'done' if unparseable."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            v = str(obj.get("verdict", "")).lower()
            if v in ("done", "refine", "clarify"):
                return v
        except Exception:
            pass
    low = text.lower()
    if "refine" in low:
        return "refine"
    return "done"


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #


def load_profile(state: AgentState) -> AgentState:
    """Load the saved file + build the privacy-safe profile; load prior turns.

    The DataFrame is loaded here and cached on the state under a private key so
    execute_code uses the SAME full frame. Fatal on missing/corrupt file.
    """
    try:
        from db.models import DatasetRow, MessageRow
        from db.session import create_db_session

        dataset_id = state["dataset_id"]
        with create_db_session() as session:
            ds = session.get(DatasetRow, dataset_id)
            if ds is None:
                return {**state, "error": f"Dataset {dataset_id} not found"}
            file_path = ds.file_path
            profile = json.loads(ds.profile_json)

            history: list = []
            conv_id = state.get("conversation_id")
            if conv_id:
                rows = (
                    session.query(MessageRow)
                    .filter(MessageRow.conversation_id == conv_id)
                    .order_by(MessageRow.created_at.asc())
                    .all()
                )
                history = [{"role": r.role, "content": r.content} for r in rows]

        df = load_csv(file_path)
        _log.info("load_profile", run_id=state.get("run_id"), rows=len(df))
        return {
            **state,
            "profile": profile,
            "history": history,
            "_df": df,  # private: full frame, never sent to the LLM
        }
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"load_profile failed: {exc}"}


def plan(state: AgentState) -> AgentState:
    try:
        system = _prompt("plan.md")
        user = (
            f"Dataset profile:\n{_profile_text(state['profile'])}\n\n"
            f"Prior turns:\n{_history_text(state.get('history', []))}\n\n"
            f"Question: {state['question']}"
        )
        out = LLMClient().call_model(user, system=system)
        _log.info("plan", run_id=state.get("run_id"))
        return {**state, "plan": (out or "").strip()}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"plan failed: {exc}"}


def generate_code(state: AgentState) -> AgentState:
    try:
        system = _prompt("generate_code.md")
        parts = [
            f"Dataset profile:\n{_profile_text(state['profile'])}",
            f"Plan:\n{state.get('plan', '')}",
            f"Question: {state['question']}",
        ]
        prev = state.get("execution") or {}
        if prev.get("error") and state.get("code"):
            parts.append(
                "Your previous attempt failed. Previous code:\n"
                f"```python\n{state['code']}\n```\n"
                f"Execution error:\n{prev['error']}\n"
                "Fix the error and output corrected code."
            )
        out = LLMClient().call_model("\n\n".join(parts), system=system)
        code = _extract_code(out or "")
        _log.info("generate_code", run_id=state.get("run_id"))
        return {**state, "code": code}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"generate_code failed: {exc}"}


def execute_code(state: AgentState) -> AgentState:
    """Run the snippet against the FULL DataFrame. No LLM call. Never fatal on
    an execution error — that feeds the refine loop."""
    try:
        df = state.get("_df")
        if df is None:
            return {**state, "error": "execute_code: no DataFrame loaded"}
        result = execute_pandas(state.get("code", ""), df)
        _log.info(
            "execute_code",
            run_id=state.get("run_id"),
            ok=result.error is None,
        )
        return {**state, "execution": result.to_dict()}
    except Exception as exc:  # noqa: BLE001
        # Defensive: executor captures errors, but guard the node anyway.
        return {**state, "execution": {"error": str(exc), "stdout": "", "result_preview": None}}


def inspect_result(state: AgentState) -> AgentState:
    """LLM judges done/refine. Increments the iteration counter."""
    iteration = state.get("iteration", 0) + 1
    try:
        execution = state.get("execution") or {}
        system = _prompt("inspect.md")
        user = (
            f"Question: {state['question']}\n\n"
            f"Code:\n```python\n{state.get('code', '')}\n```\n\n"
            f"Result preview:\n{execution.get('result_preview')}\n\n"
            f"Execution error: {execution.get('error')}"
        )
        out = LLMClient().call_model(user, system=system)
        verdict = _parse_verdict(out or "")
        # An execution error always warrants a refine attempt.
        if execution.get("error"):
            verdict = "refine"
        _log.info("inspect_result", run_id=state.get("run_id"), verdict=verdict, iteration=iteration)
        return {**state, "verdict": verdict, "iteration": iteration}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"inspect_result failed: {exc}", "iteration": iteration}


def answer(state: AgentState) -> AgentState:
    """Phrase the plain-English answer + 2-3 follow-ups."""
    try:
        execution = state.get("execution") or {}
        system = _prompt("answer.md")
        user = (
            f"Question: {state['question']}\n\n"
            f"Result preview:\n{execution.get('result_preview')}\n\n"
            f"Execution error (if any): {execution.get('error')}"
        )
        out = LLMClient().call_model(user, system=system) or ""
        answer_text, suggestions = _split_answer(out)
        _log.info("answer", run_id=state.get("run_id"))
        return {**state, "answer": answer_text, "suggestions": suggestions}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"answer failed: {exc}"}


def _split_answer(text: str) -> tuple[str, list[str]]:
    """Separate the answer body from a trailing 'Follow-ups:' list."""
    suggestions: list[str] = []
    body = text
    m = re.search(r"(?im)^follow[- ]?ups?:\s*$", text)
    if m:
        body = text[: m.start()].strip()
        tail = text[m.end():]
        for line in tail.splitlines():
            line = line.strip()
            if line.startswith("-"):
                s = line.lstrip("- ").strip()
                if s:
                    suggestions.append(s)
    return body.strip(), suggestions[:3]


def finalize(state: AgentState) -> AgentState:
    """Persist the completed run + the assistant message turn."""
    status = "completed"
    _persist_run(state, status=status)
    return {**state, "status": status}


def handle_error(state: AgentState) -> AgentState:
    """Record the run as failed."""
    _persist_run(state, status="failed")
    return {**state, "status": "failed"}


def _persist_run(state: AgentState, *, status: str) -> None:
    from db.models import ConversationRow, MessageRow, RunRow
    from db.session import create_db_session

    run_id = state.get("run_id")
    if not run_id:
        return
    execution = state.get("execution") or {}
    tokens = state.get("tokens") or {}
    try:
        with create_db_session() as session:
            run = session.get(RunRow, run_id)
            if run is None:
                return
            run.plan = state.get("plan")
            run.code = state.get("code")
            run.result_preview = execution.get("result_preview")
            run.answer = state.get("answer")
            run.status = status
            run.error_message = state.get("error")
            run.iterations = state.get("iteration", 0)
            run.prompt_tokens = int(tokens.get("prompt", 0) or 0)
            run.completion_tokens = int(tokens.get("completion", 0) or 0)
            run.cost_usd = float(state.get("cost_usd", 0.0) or 0.0)
            run.completed_at = _now()

            # Persist the assistant turn for conversation memory.
            if status == "completed" and state.get("answer"):
                conv_id = state.get("conversation_id")
                if conv_id and session.get(ConversationRow, conv_id) is not None:
                    session.add(
                        MessageRow(
                            conversation_id=conv_id,
                            role="assistant",
                            content=state["answer"],
                            run_id=run_id,
                        )
                    )
    except Exception as exc:  # noqa: BLE001
        _log.error("persist_run_failed", run_id=run_id, error=str(exc))
