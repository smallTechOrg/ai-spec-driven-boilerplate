"""Agentic-loop nodes: plan -> generate_code -> execute -> verify -> finalize.

PRIVACY BOUNDARY (hard): the LLM prompt is built in `_build_llm_context` from ONLY
schema + bounded sample + aggregates + question + plan + last_error. Raw rows never
enter a prompt — the executor loads the full DataFrame from disk locally at execute
time. Any change here that puts full rows into a prompt is a privacy violation.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from graph.state import AgentState
from llm.client import LLMClient
from analysis.executor import execute_code, ExecutionError

_PROMPTS = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS / f"{name}.md").read_text(encoding="utf-8").strip()


def _build_llm_context(state: AgentState) -> str:
    """Construct the data-derived context for a prompt.

    ONLY schema, bounded sample, and aggregates are included — never full rows.
    """
    parts = [
        f"SCHEMA:\n{json.dumps(state.get('schema', {}), default=str)}",
        f"AGGREGATES:\n{json.dumps(state.get('aggregates', {}), default=str)}",
        f"SAMPLE (bounded — {len(state.get('sample', []))} rows only):\n"
        f"{json.dumps(state.get('sample', []), default=str)}",
        f"QUESTION:\n{state.get('question', '')}",
    ]
    if state.get("plan"):
        parts.append(f"PLAN:\n{state['plan']}")
    if state.get("last_error"):
        parts.append(
            f"PREVIOUS ATTEMPT FAILED WITH ERROR:\n{state['last_error']}\n"
            f"PREVIOUS CODE:\n{state.get('code', '')}"
        )
    return "\n\n".join(parts)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:python)?\s*\n(.*?)\n```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def plan(state: AgentState) -> AgentState:
    try:
        out = LLMClient().call_model(
            _build_llm_context(state), system=_load_prompt("plan")
        )
        return {**state, "plan": out.strip()}
    except Exception as exc:  # LLM/config failure is fatal (e.g. missing key)
        return {**state, "error": str(exc)}


def generate_code(state: AgentState) -> AgentState:
    try:
        out = LLMClient().call_model(
            _build_llm_context(state), system=_load_prompt("generate_code")
        )
        return {**state, "code": _strip_code_fences(out)}
    except Exception as exc:
        return {**state, "error": str(exc)}


def _load_dataframe(state: AgentState) -> pd.DataFrame:
    path = state.get("storage_path")
    if not path:
        raise ExecutionError("No storage_path on state — cannot load dataset.")
    return pd.read_csv(path)


def execute(state: AgentState) -> AgentState:
    """Run the generated code LOCALLY against the FULL DataFrame."""
    try:
        df = _load_dataframe(state)
    except Exception as exc:
        # Loading the dataset failing is fatal (not recoverable by regeneration).
        return {**state, "error": f"Failed to load dataset: {exc}"}

    try:
        out = execute_code(state.get("code", ""), df)
        return {
            **state,
            "exec_result": out["result"],
            "chart_spec": out["chart_spec"],
            "last_error": None,
        }
    except ExecutionError as exc:
        # Recoverable — feed back to the loop for regeneration.
        return {**state, "exec_result": None, "last_error": str(exc)}


def verify(state: AgentState) -> AgentState:
    """Rule-based check that the result is well-formed and non-empty."""
    if state.get("last_error"):
        return state
    result = state.get("exec_result")
    if result is None or (isinstance(result, (list, dict)) and len(result) == 0):
        return {**state, "last_error": "Result was empty or missing after verify."}
    return {**state, "last_error": None}


def finalize(state: AgentState) -> AgentState:
    """Produce prose grounded in the locally-computed result; status completed."""
    context = (
        f"QUESTION:\n{state.get('question', '')}\n\n"
        f"RESULT:\n{json.dumps(state.get('exec_result'), default=str)}"
    )
    try:
        answer = LLMClient().call_model(context, system=_load_prompt("finalize"))
    except Exception:
        # Prose is non-critical — fall back to a deterministic summary.
        answer = f"Result: {json.dumps(state.get('exec_result'), default=str)}"
    return {
        **state,
        "answer": answer.strip(),
        "status": "completed",
        "steps_taken": state.get("step", 0) + 1,
    }


def handle_error(state: AgentState) -> AgentState:
    """Cap-hit or fatal error: status failed, with what was tried."""
    if state.get("error"):
        message = state["error"]
    else:
        message = (
            f"Gave up after {state.get('step', 0) + 1} attempts. "
            f"Last error: {state.get('last_error', 'unknown')}."
        )
    return {
        **state,
        "status": "failed",
        "error_message": message,
        "steps_taken": state.get("step", 0) + 1,
    }
