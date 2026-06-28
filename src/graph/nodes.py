"""PLAN-THEN-EXECUTE graph nodes for the Local Data Analyst.

PRIVACY BOUNDARY (structural):
- The ONLY nodes that build LLM prompts are `plan`, `narrate`, and
  `suggest_follow_ups`. Their prompt builders (`_plan_prompt`, `_narrate_prompt`,
  `_follow_ups_prompt`) accept ONLY `schema` / `profile` / `aggregates`. They are
  given no access to `query_rows`.
- `query_rows` (raw result rows) is written ONLY by `local_execute` and read ONLY
  by `aggregate`. No prompt-building code reads `query_rows`.
- `local_execute` (which touches raw data) makes NO LLM call.
- `aggregate` is the single gate: it reduces raw rows to derived numbers + column
  metadata + low-cardinality category labels via `build_aggregates`. Only that
  output (`aggregates`), plus `schema`, flows to `narrate`/`suggest_follow_ups`.
  Verbatim high-cardinality cell values (PII, free text, ids) can never cross.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import structlog

from data.cost import estimate_cost
from data.duckdb_engine import DatasetRef, QueryError, duckdb_query
from data.profiler import profile_dataset, schema_from_profile
from domain.ask import Narration, Plan
from graph.aggregate_gate import build_aggregates
from graph.state import AgentState
from llm.client import LLMClient

log = structlog.get_logger(__name__)

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

# Transient-error retry policy for Gemini (network/rate/5xx).
_MAX_RETRIES = 2
_BACKOFF_BASE_S = 1.5

# PARSE-failure retry policy: if a (transport-OK) response can't be parsed into
# the expected structured shape, re-ask the model a small fixed number of times
# before surfacing a failed run. Distinct from transient-error backoff above.
# Real-Gemini flash occasionally emits a malformed mid-object JSON; a clean
# re-ask almost always succeeds, keeping the first user ask first-time-right.
_MAX_PARSE_RETRIES = 2


def _load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8").strip()


# --------------------------------------------------------------------------- #
# LLM helpers (retry + JSON parsing)
# --------------------------------------------------------------------------- #

def _call_with_retry(system: str, user: str, *, json_mode: bool = False) -> tuple[str, int, int]:
    """Call the model with exponential backoff on transient errors.

    `json_mode` asks the provider for structured `application/json` output (set
    at client construction so the privacy spy's intercepted `call_model_usage`
    signature is untouched). Returns (text, prompt_tokens, completion_tokens).
    Raises on exhaustion.
    """
    client = LLMClient(json_mode=json_mode)
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            result = client.call_model_usage(user, system=system)
            return result.text, result.prompt_tokens, result.completion_tokens
        except Exception as exc:  # noqa: BLE001 — retry then surface
            last_exc = exc
            if attempt < _MAX_RETRIES and _is_transient(exc):
                time.sleep(_BACKOFF_BASE_S * (2 ** attempt))
                continue
            break
    raise last_exc  # type: ignore[misc]


def _call_json_with_parse_retry(
    system: str, user: str, parse: Callable[[str], Any]
) -> tuple[Any, int, int]:
    """Call the model for JSON and parse it, retrying on PARSE failure.

    Requests structured `application/json` output, then runs `parse(text)`
    (extract + pydantic-validate). If parsing fails on a transport-OK response,
    re-asks up to `_MAX_PARSE_RETRIES` times. Tokens from EVERY attempt are
    accumulated so cost stays real even across a retry. Surfaces the last parse
    error (or transient error) when the budget is exhausted — a genuinely
    unrecoverable response still becomes a transparent failed run, never a
    fabricated result.

    Returns (parsed, total_prompt_tokens, total_completion_tokens).
    """
    total_pt = 0
    total_ct = 0
    last_exc: Exception | None = None
    for attempt in range(_MAX_PARSE_RETRIES + 1):
        text, pt, ct = _call_with_retry(system, user, json_mode=True)
        total_pt += int(pt or 0)
        total_ct += int(ct or 0)
        try:
            return parse(text), total_pt, total_ct
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            last_exc = exc
            log.warning(
                "llm_json_parse_retry",
                attempt=attempt + 1,
                max_attempts=_MAX_PARSE_RETRIES + 1,
                error=str(exc),
            )
            continue
    raise last_exc  # type: ignore[misc]


def _is_transient(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(s in text for s in ("rate", "429", "500", "503", "timeout", "unavailable"))


def _extract_json(text: str) -> Any:
    """Parse a JSON object/array from a model response, tolerating code fences."""
    if not text:
        raise ValueError("empty model response")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # strip ```json ... ``` fences
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # find the first { ... } or [ ... ] span
        for open_c, close_c in (("{", "}"), ("[", "]")):
            start = cleaned.find(open_c)
            end = cleaned.rfind(close_c)
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
        raise


def _add_tokens(state: AgentState, prompt_tokens: int, completion_tokens: int) -> dict:
    pt = state.get("prompt_tokens", 0) + int(prompt_tokens or 0)
    ct = state.get("completion_tokens", 0) + int(completion_tokens or 0)
    return {
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "est_usd": estimate_cost(pt, ct),
    }


# --------------------------------------------------------------------------- #
# Prompt builders — accept ONLY schema / profile / aggregates (no query_rows)
# --------------------------------------------------------------------------- #

def _plan_prompt(question: str, schema: list[dict], profile: dict, messages: list[dict]) -> str:
    history = ""
    if messages:
        recent = messages[-6:]
        turns = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in recent)
        history = f"\nRecent conversation:\n{turns}\n"
    return (
        f"Question: {question}\n"
        f"{history}"
        f"\nColumn schema (name, type):\n{json.dumps(schema)}\n"
        f"\nDataset profile (counts/stats only — no rows):\n{json.dumps(profile)}\n"
    )


def _narrate_prompt(question: str, schema: list[dict], aggregates: dict) -> str:
    return (
        f"Question: {question}\n"
        f"\nColumn schema (name, type):\n{json.dumps(schema)}\n"
        f"\nAggregate result (the ONLY query data — already summarized):\n"
        f"{json.dumps(aggregates)}\n"
    )


def _follow_ups_prompt(question: str, schema: list[dict], aggregates: dict) -> str:
    return (
        f"Original question: {question}\n"
        f"\nColumn schema (name, type):\n{json.dumps(schema)}\n"
        f"\nAggregate result:\n{json.dumps(aggregates)}\n"
    )


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #

def profile(state: AgentState) -> AgentState:
    """Load schema + profile via local DuckDB queries (no LLM)."""
    try:
        if state.get("schema") and state.get("profile"):
            return {**state}
        ref = state.get("dataset_ref")
        if ref is None:
            return {**state, "error": "No dataset reference available to profile."}
        prof = profile_dataset(ref if isinstance(ref, DatasetRef) else DatasetRef(**ref))
        return {**state, "profile": prof, "schema": schema_from_profile(prof)}
    except Exception as exc:  # noqa: BLE001
        log.error("profile_failed", run_id=state.get("run_id"), error=str(exc))
        return {**state, "error": f"Profiling failed: {exc}"}


def plan(state: AgentState) -> AgentState:
    """Draft plan + SQL from schema/profile only (LLM). NO raw rows."""
    try:
        system = _load_prompt("plan.md")
        user = _plan_prompt(
            state["question"],
            state.get("schema", []),
            state.get("profile", {}),
            state.get("messages", []),
        )
        parsed, pt, ct = _call_json_with_parse_retry(
            system, user, lambda t: Plan(**_extract_json(t))
        )
        if not parsed.sql.strip():
            return {**state, "error": "The planner did not produce any SQL."}
        update = {
            **state,
            "plan_steps": parsed.steps,
            "generated_sql": parsed.sql.strip(),
        }
        update.update(_add_tokens(state, pt, ct))
        return update
    except Exception as exc:  # noqa: BLE001
        log.error("plan_failed", run_id=state.get("run_id"), error=str(exc))
        return {**state, "error": f"Planning failed: {exc}"}


def local_execute(state: AgentState) -> AgentState:
    """Run the generated SQL LOCALLY (no LLM). Raw rows stay in state only."""
    sql = state.get("generated_sql", "")
    try:
        ref = state.get("dataset_ref")
        ref = ref if isinstance(ref, DatasetRef) else DatasetRef(**ref)
        rows, cols = duckdb_query(sql, ref)
        log.info(
            "local_execute_ok",
            run_id=state.get("run_id"),
            row_count=len(rows),
        )
        return {**state, "query_rows": rows, "query_columns": cols}
    except QueryError as exc:
        # Preserve the attempted SQL so the user always sees what was tried.
        log.error("local_execute_rejected", run_id=state.get("run_id"), error=str(exc))
        return {**state, "error": f"Query failed: {exc}", "generated_sql": sql}
    except Exception as exc:  # noqa: BLE001
        log.error("local_execute_failed", run_id=state.get("run_id"), error=str(exc))
        return {**state, "error": f"Query failed: {exc}", "generated_sql": sql}


def aggregate(state: AgentState) -> AgentState:
    """Privacy gate: STRUCTURALLY reduce raw rows to safe summaries.

    Only this node's output (`aggregates`) — plus `schema` — flows to the LLM
    narration nodes. Raw `query_rows` never proceed past here. The summarizer
    (`build_aggregates`) emits ONLY derived numbers, column metadata, and
    low-cardinality category labels — never verbatim high-cardinality cell values
    (PII, free text, ids), regardless of what SELECT the planner produced. This
    holds even for `SELECT *` / row-level queries, because the gate inspects the
    actual result and lets a string value cross only when it is a low-cardinality
    grouping label, never a per-row secret.
    """
    try:
        rows = state.get("query_rows", [])
        cols = state.get("query_columns", [])
        # The dataset-wide profile (derived numbers only) lets the gate judge a
        # grouping label's cardinality against the WHOLE dataset, not a slice.
        profile = state.get("profile", {})
        aggregates = build_aggregates(rows, cols, profile)
        return {**state, "aggregates": aggregates}
    except Exception as exc:  # noqa: BLE001
        log.error("aggregate_failed", run_id=state.get("run_id"), error=str(exc))
        return {**state, "error": f"Aggregation failed: {exc}"}


def narrate(state: AgentState) -> AgentState:
    """Narrate aggregates (LLM). Receives schema + aggregates only."""
    try:
        system = _load_prompt("narrate.md")
        user = _narrate_prompt(
            state["question"],
            state.get("schema", []),
            state.get("aggregates", {}),
        )
        narration, pt, ct = _call_json_with_parse_retry(
            system, user, lambda t: Narration(**_extract_json(t))
        )
        update = {
            **state,
            "answer": narration.answer,
            "key_stats": [k.model_dump() for k in narration.key_stats],
            "chart_spec": narration.chart_spec.model_dump() if narration.chart_spec else {},
            "summary_table": narration.summary_table.model_dump() if narration.summary_table else {},
            "insight": narration.insight,
        }
        update.update(_add_tokens(state, pt, ct))
        return update
    except Exception as exc:  # noqa: BLE001
        log.error("narrate_failed", run_id=state.get("run_id"), error=str(exc))
        return {**state, "error": f"Narration failed: {exc}"}


def suggest_follow_ups(state: AgentState) -> AgentState:
    """Suggest 2–3 follow-ups (LLM, non-fatal). Schema + aggregates only."""
    try:
        system = _load_prompt("follow_ups.md")
        user = _follow_ups_prompt(
            state["question"],
            state.get("schema", []),
            state.get("aggregates", {}),
        )
        def _parse_list(t: str) -> list:
            parsed = _extract_json(t)
            if not isinstance(parsed, list):
                raise ValueError("follow-ups response was not a JSON array")
            return parsed

        parsed, pt, ct = _call_json_with_parse_retry(system, user, _parse_list)
        follow_ups = [str(q) for q in parsed][:3]
        update = {**state, "follow_ups": follow_ups}
        update.update(_add_tokens(state, pt, ct))
        return update
    except Exception as exc:  # noqa: BLE001 — non-fatal, degrade to empty
        log.warning("follow_ups_failed", run_id=state.get("run_id"), error=str(exc))
        return {**state, "follow_ups": []}


def finalize(state: AgentState) -> AgentState:
    return {**state, "status": "completed", "checkpoint": "finalize"}


def handle_error(state: AgentState) -> AgentState:
    return {**state, "status": "failed", "checkpoint": "handle_error"}
