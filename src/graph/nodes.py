"""LangGraph capability nodes for the CSV-analysis agent.

Pipeline: load_profile -> build_prompt -> answer -> finalize, with a shared
handle_error sink. The privacy data boundary is enforced in ``build_prompt``,
which serializes ONLY the question + derived profile into the LLM prompt — the
raw DataFrame never enters graph state.
"""

import json
import time
from pathlib import Path

import pandas as pd
from pandas.api import types as ptypes

from datasets.profiler import build_profile
from datasets.store import DatasetError, dataset_path
from graph.state import AgentState
from llm.client import LLMClient
from observability.events import get_logger

logger = get_logger("graph.nodes")

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "answer.md"

# Caps for the derived group aggregates that cross the boundary. These keep the
# prompt token-frugal and ensure no full column/row ever leaks — only grouped
# sums/means for a bounded number of low-cardinality categorical columns.
_MAX_GROUP_COLS = 5          # categorical columns to break down by
_MAX_NUMERIC_COLS = 5        # numeric columns to aggregate
_MAX_GROUPS_PER_COL = 25     # distinct categories kept per categorical column

# Hard ceiling on the single Gemini call so a hung request fails gracefully.
_ANSWER_TIMEOUT_S = 60.0

# Human-readable failure copy (never a stack trace) routed to handle_error.
_PROFILE_FAILURE_COPY = "Dataset not found or unreadable."
_PROMPT_FAILURE_COPY = "Could not prepare the question for analysis. Please try again."
_LLM_FAILURE_COPY = "Could not reach the analysis model — please retry."


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


def load_profile(state: AgentState) -> AgentState:
    """Re-profile the dataset's LOCAL CSV with pandas.

    Writes only the derived ``profile`` dict to state. The raw DataFrame stays
    inside ``build_profile`` and never reaches graph state — the local side of
    the privacy boundary.
    """
    dataset_id = state.get("dataset_id")
    try:
        profile = build_profile(dataset_id)
    except DatasetError as exc:
        logger.warning("load_profile_failed", dataset_id=dataset_id, error=str(exc))
        return {**state, "error": exc.message}
    except Exception as exc:  # noqa: BLE001 - surface as human copy, never a crash
        logger.error("load_profile_error", dataset_id=dataset_id, error=str(exc))
        return {**state, "error": _PROFILE_FAILURE_COPY}

    # Enrich the profile with bounded grouped aggregates (categorical x numeric
    # sums + means) computed LOCALLY. These are derived statistics — never raw
    # rows — and are what let the model answer "which category has the highest
    # total <numeric>?" from the profile alone. The DataFrame stays local here.
    try:
        profile = {**profile, "group_aggregates": _group_aggregates(dataset_id)}
    except Exception as exc:  # noqa: BLE001 - aggregates are best-effort, never fatal
        logger.warning("group_aggregates_failed", dataset_id=dataset_id, error=str(exc))

    logger.info(
        "load_profile",
        dataset_id=dataset_id,
        row_count=profile.get("row_count"),
        n_columns=len(profile.get("columns", [])),
    )
    return {**state, "profile": profile}


def _group_aggregates(dataset_id: str) -> dict:
    """Compute capped per-categorical-column grouped sums/means for numeric columns.

    Returns ``{cat_col: {num_col: {group: {"sum", "mean", "count"}}}}`` for a
    bounded number of low-cardinality categorical columns and numeric columns.
    Only aggregated scalars cross the boundary — the raw DataFrame stays local and
    is discarded when this function returns.
    """
    df = pd.read_csv(dataset_path(dataset_id))

    numeric_cols = [
        str(c)
        for c in df.columns
        if ptypes.is_numeric_dtype(df[c]) and not ptypes.is_bool_dtype(df[c])
    ][:_MAX_NUMERIC_COLS]

    # Prefer low-cardinality, non-numeric columns as grouping keys.
    cat_cols = [
        str(c)
        for c in df.columns
        if not (ptypes.is_numeric_dtype(df[c]) and not ptypes.is_bool_dtype(df[c]))
        and df[c].nunique(dropna=True) <= _MAX_GROUPS_PER_COL
    ][:_MAX_GROUP_COLS]

    aggregates: dict[str, dict] = {}
    for cat in cat_cols:
        per_numeric: dict[str, dict] = {}
        for num in numeric_cols:
            grouped = df.groupby(cat, dropna=True)[num]
            sums = grouped.sum()
            means = grouped.mean()
            counts = grouped.count()
            per_group: dict[str, dict] = {}
            for group in sums.index[:_MAX_GROUPS_PER_COL]:
                per_group[str(group)] = {
                    "sum": _round(sums[group]),
                    "mean": _round(means[group]),
                    "count": int(counts[group]),
                }
            per_numeric[num] = per_group
        if per_numeric:
            aggregates[cat] = per_numeric
    return aggregates


def _round(value: object) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return round(f, 4)


def build_prompt(state: AgentState) -> AgentState:
    """Serialize ONLY ``{question, profile}`` into the LLM user prompt.

    THE BOUNDARY-ENFORCEMENT NODE: it provably constructs the LLM input from the
    derived profile alone — never the raw rows or the DataFrame. A test asserts no
    full data row appears in the resulting ``prompt``.
    """
    try:
        payload = {
            "question": state.get("question"),
            "profile": state.get("profile"),
        }
        # Compact JSON keeps tokens (and cost) low; the profile is already capped
        # to schema + summary stats + <=5 truncated examples by the profiler.
        prompt = json.dumps(payload, separators=(",", ":"), default=str)
    except Exception as exc:  # noqa: BLE001
        logger.error("build_prompt_failed", error=str(exc))
        return {**state, "error": _PROMPT_FAILURE_COPY}

    logger.info("build_prompt", prompt_len=len(prompt))
    return {**state, "prompt": prompt}


def answer(state: AgentState) -> AgentState:
    """The single Gemini call — sends the boundary-safe prompt, stores the answer.

    Wrapped with a timeout + try/except; any failure sets ``error`` and routes to
    handle_error. Logs model + prompt length + latency + completion length — never
    raw rows or the API key.
    """
    prompt = state.get("prompt", "")
    system = _load_system_prompt()
    started = time.monotonic()

    try:
        result = _call_with_timeout(prompt, system, _ANSWER_TIMEOUT_S)
    except TimeoutError as exc:
        logger.error("answer_timeout", error=str(exc), timeout_s=_ANSWER_TIMEOUT_S)
        return {**state, "error": _LLM_FAILURE_COPY}
    except Exception as exc:  # noqa: BLE001 - graceful failure, never a stack trace
        logger.error("answer_failed", error=str(exc))
        return {**state, "error": _LLM_FAILURE_COPY}

    latency_ms = int((time.monotonic() - started) * 1000)

    if not result or not result.strip():
        logger.error("answer_empty", latency_ms=latency_ms)
        return {**state, "error": _LLM_FAILURE_COPY}

    from config.settings import get_settings

    logger.info(
        "answer",
        model=get_settings().llm_model or "default",
        prompt_len=len(prompt),
        latency_ms=latency_ms,
        completion_len=len(result),
    )
    return {**state, "answer": result.strip()}


def _call_with_timeout(prompt: str, system: str, timeout_s: float) -> str:
    """Run the single Gemini call under a hard wall-clock timeout.

    Uses a worker thread so a hung network call cannot block the run indefinitely.
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(lambda: LLMClient().call_model(prompt, system=system))
        try:
            return future.result(timeout=timeout_s)
        except FuturesTimeout as exc:
            raise TimeoutError(
                f"Gemini call exceeded {timeout_s:.0f}s"
            ) from exc


def finalize(state: AgentState) -> AgentState:
    return {**state, "status": "completed"}


def handle_error(state: AgentState) -> AgentState:
    logger.warning(
        "run_failed",
        run_id=state.get("run_id"),
        error=state.get("error"),
    )
    return {**state, "status": "failed"}
