"""Analyze-run entry point: create the analyses row, run the agentic loop, persist."""
from __future__ import annotations

import time

from graph.agent import agentic_ai
from graph.state import AgentState
from db.session import create_db_session
from db.models import Analysis, Dataset
from config.settings import get_settings
from observability.events import get_logger, configure_logging

configure_logging(get_settings().log_level)
log = get_logger("analyze")


def _aggregates_from_profile(profile: dict) -> dict:
    """Derive the per-column aggregates block from the stored profile.

    Privacy-safe: aggregates only, no raw rows.
    """
    agg: dict[str, dict] = {}
    for col in profile.get("columns", []):
        entry = {
            k: col[k]
            for k in ("missing_count", "distinct_count", "min", "max", "mean", "top_values")
            if k in col
        }
        agg[col["name"]] = entry
    return agg


def _schema_from_profile(profile: dict) -> dict:
    return {c["name"]: c["dtype"] for c in profile.get("columns", [])}


def run_analysis(dataset_id: str, question: str) -> str:
    """Run one analysis against a dataset. Returns the analyses row id.

    Raises ValueError if the dataset does not exist.
    """
    settings = get_settings()

    with create_db_session() as session:
        dataset = session.get(Dataset, dataset_id)
        if dataset is None:
            raise ValueError(f"Unknown dataset_id: {dataset_id}")
        storage_path = dataset.storage_path
        profile = dataset.profile

        run = Analysis(dataset_id=dataset_id, question=question, status="running")
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AgentState = {
        "run_id": run_id,
        "dataset_id": dataset_id,
        "storage_path": storage_path,
        "question": question,
        "schema": _schema_from_profile(profile),
        "sample": profile.get("sample", []),
        "aggregates": _aggregates_from_profile(profile),
        "step": 0,
        "max_steps": settings.max_steps,
        "status": "running",
        "error": None,
        "last_error": None,
    }

    started = time.monotonic()
    final = agentic_ai.invoke(initial)
    latency_ms = round((time.monotonic() - started) * 1000)

    status = final.get("status", "failed")
    steps_taken = final.get("steps_taken", final.get("step", 0) + 1)

    with create_db_session() as session:
        run = session.get(Analysis, run_id)
        run.status = status
        run.code = final.get("code")
        run.result = final.get("exec_result")
        run.chart_spec = final.get("chart_spec")
        run.answer = final.get("answer")
        run.steps_taken = steps_taken
        run.error_message = final.get("error_message") or final.get("error")

    # Observability: one structured line per end-to-end analyze run (no raw rows).
    log.info(
        "analyze_run",
        run_id=run_id,
        dataset_id=dataset_id,
        question=question[:200],
        status=status,
        steps_taken=steps_taken,
        latency_ms=latency_ms,
    )

    return run_id
