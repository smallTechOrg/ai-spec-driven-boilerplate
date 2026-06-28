"""Analysis runner — creates the run row, invokes the graph, persists the result.

Honest failure: if the agent cannot compute (LLM down, dataset missing, code never
produced a result), the run is marked `failed` with a message — never a crash and
never a fabricated answer.
"""
from __future__ import annotations

from analysis.profile import profile_dataframe
from analysis.loader import load_dataframe_for_dataset
from config.settings import get_settings
from db.models import AnalysisRun, Dataset, DatasetProfile
from db.session import create_db_session, init_db
from graph.agent import agentic_ai
from graph.state import AgentState
from observability.events import get_logger

_log = get_logger("datachat.runner")


def _load_profile(session, dataset_id: str) -> dict | None:
    profile = (
        session.query(DatasetProfile)
        .filter(DatasetProfile.dataset_id == dataset_id)
        .order_by(DatasetProfile.created_at.desc())
        .first()
    )
    if profile is None:
        return None
    return {
        "columns": profile.columns,
        "row_count": profile.row_count,
        "column_count": len(profile.columns or []),
    }


def run_analysis(dataset_id: str, question: str) -> str:
    """Run one analysis question. Returns the AnalysisRun id (persisted)."""
    init_db()

    with create_db_session() as session:
        dataset = session.get(Dataset, dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset {dataset_id} not found")
        profile = _load_profile(session, dataset_id)
        run = AnalysisRun(
            dataset_id=dataset_id, question=question, status="pending"
        )
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AgentState = {
        "run_id": run_id,
        "dataset_id": dataset_id,
        "question": question,
        "profile": profile,
        "history": [],
        "step": 0,
        "max_steps": get_settings().max_steps,
        "attempts": [],
        "tokens": {"prompt": 0, "completion": 0, "total": 0},
        "cost_usd": 0.0,
        "error": None,
    }

    try:
        final = agentic_ai.invoke(initial)
    except Exception as exc:  # never crash the request — record an honest failure
        _log.error("analysis_run_crashed", run_id=run_id, error=str(exc))
        final = {"status": "failed", "error": f"unexpected error: {exc}"}

    tokens = final.get("tokens") or {"prompt": 0, "completion": 0, "total": 0}
    status = final.get("status") or ("failed" if final.get("error") else "completed")
    error = final.get("error")

    with create_db_session() as session:
        from datetime import datetime, timezone

        run = session.get(AnalysisRun, run_id)
        run.plan = final.get("plan")
        run.code = final.get("code")
        run.result_summary = final.get("result_summary")
        run.answer = final.get("answer")
        run.prompt_tokens = int(tokens.get("prompt", 0))
        run.completion_tokens = int(tokens.get("completion", 0))
        run.total_tokens = int(tokens.get("total", 0))
        run.cost_usd = float(final.get("cost_usd") or 0.0)
        run.status = status
        run.error_message = error
        run.completed_at = datetime.now(timezone.utc)

    _log.info(
        "analysis_run_done",
        run_id=run_id,
        status=status,
        total_tokens=int(tokens.get("total", 0)),
    )
    return run_id


def profile_and_store(
    session,
    *,
    name: str,
    kind: str,
    file_path: str,
    size_bytes: int,
    dataset_id: str | None = None,
) -> tuple[Dataset, DatasetProfile]:
    """Profile an uploaded file locally and persist Dataset + DatasetProfile."""
    df = load_dataframe(file_path, kind)
    prof = profile_dataframe(df)
    dataset = Dataset(
        name=name,
        kind=kind,
        file_path=file_path,
        row_count=prof["row_count"],
        column_count=prof["column_count"],
        size_bytes=size_bytes,
    )
    if dataset_id is not None:
        dataset.id = dataset_id
    session.add(dataset)
    session.flush()
    profile = DatasetProfile(
        dataset_id=dataset.id,
        columns=prof["columns"],
        row_count=prof["row_count"],
    )
    session.add(profile)
    session.flush()
    return dataset, profile


def load_dataframe(file_path: str, kind: str):
    from analysis.profile import load_dataframe as _load

    return _load(file_path, kind=kind)
