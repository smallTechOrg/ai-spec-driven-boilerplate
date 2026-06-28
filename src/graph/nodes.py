"""LangGraph nodes for the DataChat analysis graph.

Privacy spine: the LLM-facing nodes (plan / generate_code / finalize) build their
prompts ONLY from the question + profile + bounded result summaries. The
`build_*_prompt` functions are the single point where each prompt is assembled, so
tests can assert that no raw row value ever appears. `execute_local` is the only
node that touches raw rows — it calls NO LLM.
"""
from __future__ import annotations

import json
from pathlib import Path

from analysis.cost import estimate_cost_usd
from analysis.executor import execute_code, extract_code, summarize_result  # noqa: F401
from analysis.loader import load_dataframe_for_dataset
from graph.state import AgentState
from llm.client import LLMClient

_PROMPTS = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS / name).read_text(encoding="utf-8").strip()


def _llm_safe_profile(profile: dict | None) -> dict:
    """Strip example cell values from the profile before it reaches the LLM.

    The stored/returned profile carries `sample_values` for the user's own UI, but
    those are verbatim cell values — they must NOT cross the privacy boundary into
    a Gemini prompt. The LLM only needs schema shape: column name, dtype, null
    counts, cardinality, and numeric/datetime ranges (aggregates, not rows).
    """
    if not profile:
        return {}
    safe_columns = []
    for col in profile.get("columns", []):
        safe_columns.append(
            {
                "name": col.get("name"),
                "dtype": col.get("dtype"),
                "non_null": col.get("non_null"),
                "n_unique": col.get("n_unique"),
                "min": col.get("min"),
                "max": col.get("max"),
            }
        )
    return {
        "columns": safe_columns,
        "row_count": profile.get("row_count"),
        "column_count": profile.get("column_count"),
    }


def _profile_text(profile: dict | None) -> str:
    """Render the row-free, sample-free profile for a prompt. No raw cell values."""
    return json.dumps(_llm_safe_profile(profile), indent=2, default=str)


def _accumulate_tokens(state: AgentState, result) -> AgentState:
    """Fold an LLMResult's token usage + cost into the running totals."""
    tokens = dict(state.get("tokens") or {"prompt": 0, "completion": 0, "total": 0})
    tokens["prompt"] += result.prompt_tokens
    tokens["completion"] += result.completion_tokens
    tokens["total"] += result.total_tokens
    cost = float(state.get("cost_usd") or 0.0) + estimate_cost_usd(
        result.prompt_tokens, result.completion_tokens
    )
    return {"tokens": tokens, "cost_usd": cost}


# --- Prompt builders (privacy boundary — only question + profile + summaries) ---

def build_plan_prompt(question: str, profile: dict | None) -> str:
    return (
        f"Question:\n{question}\n\n"
        f"Dataset profile (schema only, no rows):\n{_profile_text(profile)}"
    )


def build_code_prompt(
    question: str, profile: dict | None, plan: str, exec_error: str | None = None
) -> str:
    parts = [
        f"Question:\n{question}\n",
        f"Plan:\n{plan}\n",
        f"Dataset profile (schema only, no rows):\n{_profile_text(profile)}",
    ]
    if exec_error:
        parts.append(
            "\nThe previous code failed with this error. Fix it:\n" + exec_error
        )
    return "\n".join(parts)


def build_finalize_prompt(question: str, result_summary: dict | None) -> str:
    return (
        f"Question:\n{question}\n\n"
        f"Computed result summary:\n{json.dumps(result_summary or {}, default=str)}"
    )


# --- Nodes ---

def plan(state: AgentState) -> AgentState:
    try:
        prompt = build_plan_prompt(state["question"], state.get("profile"))
        result = LLMClient().call_with_usage(prompt, system=_load_prompt("plan.md"))
        return {**state, "plan": result.text.strip(), **_accumulate_tokens(state, result)}
    except Exception as exc:
        return {**state, "error": f"plan failed: {exc}"}


def generate_code(state: AgentState) -> AgentState:
    try:
        prompt = build_code_prompt(
            state["question"],
            state.get("profile"),
            state.get("plan", ""),
            state.get("exec_error"),
        )
        result = LLMClient().call_with_usage(
            prompt, system=_load_prompt("generate_code.md")
        )
        code = extract_code(result.text)
        return {**state, "code": code, **_accumulate_tokens(state, result)}
    except Exception as exc:
        return {**state, "error": f"generate_code failed: {exc}"}


def execute_local(state: AgentState) -> AgentState:
    """The privacy boundary — runs generated code locally. NO LLM call."""
    try:
        df = load_dataframe_for_dataset(state["dataset_id"])
    except Exception as exc:
        # A missing/unreadable dataset is a fatal (non-code) error.
        return {**state, "error": f"could not load dataset: {exc}"}

    outcome = execute_code(state.get("code", ""), df)
    attempts = list(state.get("attempts") or [])
    step = int(state.get("step", 0))
    if outcome.error is not None:
        attempts.append({"code": state.get("code"), "error": outcome.error})
        return {
            **state,
            "exec_error": outcome.error,
            "result_summary": None,
            "attempts": attempts,
            "step": step + 1,
        }
    attempts.append({"code": state.get("code"), "result_summary": outcome.summary})
    return {
        **state,
        "exec_error": None,
        "result_summary": outcome.summary,
        "attempts": attempts,
        "step": step + 1,
    }


def inspect(state: AgentState) -> AgentState:
    """P1: pass-through. Always routes to finalize (single pass). P3: reflection."""
    return state


def finalize(state: AgentState) -> AgentState:
    try:
        prompt = build_finalize_prompt(state["question"], state.get("result_summary"))
        result = LLMClient().call_with_usage(
            prompt, system=_load_prompt("finalize.md")
        )
        return {
            **state,
            "answer": result.text.strip(),
            "status": "completed",
            **_accumulate_tokens(state, result),
        }
    except Exception as exc:
        return {**state, "error": f"finalize failed: {exc}"}


def handle_error(state: AgentState) -> AgentState:
    return {**state, "status": "failed"}
