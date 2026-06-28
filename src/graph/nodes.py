"""LangGraph nodes for the data-analysis pipeline.

load_context -> plan -> generate_code -> execute_local -> visualize -> finalize
with a handle_error path and a single self-correction retry on execution failure.

The runner/api layer loads the Dataset + conversation history from the DB and
injects ``profile``, ``sample_rows``, ``file_path``, ``row_count`` and
``history`` into the initial state. These nodes operate purely on state, so the
graph stays independent of the DB models surface and is unit-testable.

All LLM calls go through ``llm/context.py`` (the privacy chokepoint) — never the
Gemini SDK directly. Token usage and estimated cost accumulate into state.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from analysis.executor import execute_code
from graph.state import AgentState
from llm.context import build_llm_context, call_llm
from observability.events import get_logger

logger = get_logger("nodes")

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def _emit(state: AgentState, step: str, status: str) -> None:
    cb = state.get("on_step")
    if callable(cb):
        try:
            cb(step, status)
        except Exception:  # noqa: BLE001 — observability must never break the run
            logger.warning("on_step_callback_failed", step=step, status=status)


def _accumulate_usage(state: AgentState, result) -> dict:
    return {
        "prompt_tokens": state.get("prompt_tokens", 0) + result.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + result.completion_tokens,
        "estimated_cost_usd": round(
            state.get("estimated_cost_usd", 0.0) + result.cost_usd, 8
        ),
    }


def _strip_fences(text: str) -> str:
    """Remove markdown code fences the model may add despite instructions."""
    text = text.strip()
    fence = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    # Tolerate a single leading/trailing fence line.
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json(text: str, default: Any) -> Any:
    cleaned = _strip_fences(text)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        # Try to find the first JSON array/object in the text.
        m = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        return default


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #

def load_context(state: AgentState) -> AgentState:
    """Normalise the injected dataset context into state (privacy-safe)."""
    _emit(state, "load_context", "running")
    try:
        if not state.get("question"):
            raise ValueError("question is required")
        if not state.get("file_path"):
            raise ValueError("dataset file_path is required")
        out: AgentState = {
            **state,
            "profile": state.get("profile") or [],
            "sample_rows": state.get("sample_rows") or [],
            "history": state.get("history") or [],
            "retry_count": 0,
            "prompt_tokens": state.get("prompt_tokens", 0),
            "completion_tokens": state.get("completion_tokens", 0),
            "estimated_cost_usd": state.get("estimated_cost_usd", 0.0),
            "assumptions": [],
            "error": None,
        }
        _emit(state, "load_context", "done")
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("load_context_failed", error=str(exc))
        return {**state, "error": f"load_context: {exc}"}


def plan(state: AgentState) -> AgentState:
    _emit(state, "plan", "running")
    try:
        payload = build_llm_context(
            question=state["question"],
            profile=state.get("profile"),
            sample_rows=state.get("sample_rows"),
            history=state.get("history"),
            row_count=state.get("row_count"),
        )
        result = call_llm(payload, system=_load_prompt("plan.md"))
        steps = _parse_json(result.text, default=[])
        if not isinstance(steps, list):
            steps = [str(steps)]
        plan_steps = [str(s) for s in steps][:8]
        _emit(state, "plan", "done")
        return {**state, "plan": plan_steps, **_accumulate_usage(state, result)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("plan_failed", error=str(exc))
        return {**state, "error": f"plan: {exc}"}


def generate_code(state: AgentState) -> AgentState:
    _emit(state, "generate_code", "running")
    try:
        extra: dict[str, Any] = {"plan": state.get("plan", [])}
        retry_count = state.get("retry_count", 0)
        if state.get("traceback"):
            extra["traceback"] = state["traceback"]
            extra["previous_code"] = state.get("code", "")
            retry_count += 1  # this is a self-correction pass
        payload = build_llm_context(
            question=state["question"],
            profile=state.get("profile"),
            sample_rows=state.get("sample_rows"),
            history=state.get("history"),
            row_count=state.get("row_count"),
            extra=extra,
        )
        result = call_llm(payload, system=_load_prompt("generate_code.md"))
        code = _strip_fences(result.text)
        if not code:
            raise ValueError("model returned empty code")
        _emit(state, "generate_code", "done")
        return {
            **state,
            "code": code,
            "retry_count": retry_count,
            "traceback": None,
            **_accumulate_usage(state, result),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("generate_code_failed", error=str(exc))
        return {**state, "error": f"generate_code: {exc}"}


def execute_local(state: AgentState) -> AgentState:
    """Run generated code locally over ALL rows. No LLM call."""
    _emit(state, "execute_local", "running")
    outcome = execute_code(state["code"], state["file_path"])
    if outcome["traceback"]:
        _emit(state, "execute_local", "error")
        return {
            **state,
            "result_table": None,
            "traceback": outcome["traceback"],
        }
    _emit(state, "execute_local", "done")
    return {**state, "result_table": outcome["result_table"], "traceback": None}


def visualize(state: AgentState) -> AgentState:
    _emit(state, "visualize", "running")
    assumptions = list(state.get("assumptions") or [])
    # If execution never succeeded, degrade to a best-guess (table-less) answer.
    if state.get("traceback") and state.get("result_table") is None:
        assumptions.append(
            "Code execution failed after a self-correction attempt; the answer "
            "below is a best-guess and could not be computed over the data."
        )
    try:
        result_table = state.get("result_table") or {"columns": [], "rows": [], "row_count": 0}
        payload = build_llm_context(
            question=state["question"],
            profile=state.get("profile"),
            sample_rows=state.get("sample_rows"),
            history=state.get("history"),
            row_count=state.get("row_count"),
            extra={"result_table": result_table},
        )
        result = call_llm(payload, system=_load_prompt("visualize.md"))
        parsed = _parse_json(result.text, default={})
        answer = parsed.get("answer") or result.text.strip()
        chart_spec = parsed.get("chart_spec") or {"chart_type": "none"}
        follow_ups = parsed.get("follow_ups") or []
        if not isinstance(follow_ups, list):
            follow_ups = []
        _emit(state, "visualize", "done")
        return {
            **state,
            "answer": str(answer),
            "chart_spec": chart_spec if isinstance(chart_spec, dict) else {"chart_type": "none"},
            "follow_ups": [str(f) for f in follow_ups][:3],
            "assumptions": assumptions,
            **_accumulate_usage(state, result),
        }
    except Exception as exc:  # noqa: BLE001 — degrade to table-only, never crash
        logger.warning("visualize_failed", error=str(exc))
        return {
            **state,
            "answer": state.get("answer") or "Result computed; chart unavailable.",
            "chart_spec": {"chart_type": "none"},
            "follow_ups": [],
            "assumptions": assumptions,
        }


def finalize(state: AgentState) -> AgentState:
    _emit(state, "finalize", "done")
    return {**state, "status": "completed"}


def handle_error(state: AgentState) -> AgentState:
    logger.warning("handle_error", run_id=state.get("run_id"), error=state.get("error"))
    _emit(state, "handle_error", "error")
    return {**state, "status": "failed"}
