"""Run a single ask through the PLAN-THEN-EXECUTE graph and persist the audit.

The runner is the boundary between the API and the graph: it creates the Run
row, loads the Dataset to build the local DuckDB reference + initial state,
invokes the compiled graph, then persists the full Run audit record and the
conversation Messages. It never writes raw rows to SQLite — only aggregates +
narration go into `result_summary_json`.
"""
from __future__ import annotations

import json
from typing import Any

import structlog

from data.duckdb_engine import DatasetRef
from db.models import Dataset, Message, RunRow
from db.session import create_db_session
from domain.ask import AskResponse, Cost, KeyStat
from graph.agent import agentic_ai
from graph.state import AgentState

log = structlog.get_logger(__name__)


class DatasetNotFound(Exception):
    """Raised when the ask references an unknown dataset_id."""


def _dataset_ref(ds: Dataset) -> DatasetRef:
    return DatasetRef(
        dataset_id=ds.id,
        source_path=ds.source_path,
        source_kind=ds.source_kind,
        duckdb_table=ds.duckdb_table,
        sheet_name=ds.sheet_name,
    )


def _result_summary(final: AgentState) -> dict[str, Any]:
    """Aggregates + narration only — never raw rows."""
    return {
        "answer": final.get("answer", ""),
        "key_stats": final.get("key_stats", []),
        "chart_spec": final.get("chart_spec", {}),
        "summary_table": final.get("summary_table", {}),
        "insight": final.get("insight", ""),
        "aggregates": final.get("aggregates", {}),
    }


def ask(dataset_id: str, question: str) -> AskResponse:
    """Execute one ask end-to-end and return the rich-answer envelope."""
    # Load dataset + create the pending Run row.
    with create_db_session() as session:
        ds = session.get(Dataset, dataset_id)
        if ds is None:
            raise DatasetNotFound(dataset_id)
        ref = _dataset_ref(ds)
        cached_profile = json.loads(ds.profile_json) if ds.profile_json else None

        run = RunRow(dataset_id=dataset_id, question=question, status="pending")
        session.add(run)
        session.flush()
        run_id = run.id

        # Prior conversation turns for this dataset (recent window).
        prior = (
            session.query(Message)
            .filter(Message.dataset_id == dataset_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        messages = [{"role": m.role, "content": m.content} for m in prior]

    initial: AgentState = {
        "run_id": run_id,
        "dataset_id": dataset_id,
        "question": question,
        "messages": messages,
        "dataset_ref": ref,
        "error": None,
    }
    if cached_profile:
        from data.profiler import schema_from_profile

        initial["profile"] = cached_profile
        initial["schema"] = schema_from_profile(cached_profile)

    final: AgentState = agentic_ai.invoke(initial)
    status = final.get("status", "completed")
    error = final.get("error")

    # Persist the audit record + conversation messages.
    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        run.status = status
        run.plan_json = json.dumps(final.get("plan_steps", []))
        run.generated_sql = final.get("generated_sql")
        run.result_summary_json = json.dumps(_result_summary(final))
        run.prompt_tokens = final.get("prompt_tokens", 0)
        run.completion_tokens = final.get("completion_tokens", 0)
        run.est_usd = final.get("est_usd", 0.0)
        run.error_message = error

        # Record the user turn always; the assistant turn only on success.
        session.add(
            Message(dataset_id=dataset_id, run_id=run_id, role="user", content=question)
        )
        if status == "completed" and final.get("answer"):
            session.add(
                Message(
                    dataset_id=dataset_id,
                    run_id=run_id,
                    role="assistant",
                    content=final.get("answer", ""),
                )
            )

    log.info("ask_done", run_id=run_id, status=status, est_usd=final.get("est_usd"))

    return AskResponse(
        run_id=run_id,
        status=status,
        answer=final.get("answer", ""),
        key_stats=[KeyStat(**k) for k in final.get("key_stats", [])],
        chart_spec=final.get("chart_spec") or None,
        summary_table=final.get("summary_table") or None,
        insight=final.get("insight", ""),
        follow_ups=final.get("follow_ups", []),
        plan_steps=final.get("plan_steps", []),
        generated_sql=final.get("generated_sql", "") or "",
        cost=Cost(
            prompt_tokens=final.get("prompt_tokens", 0),
            completion_tokens=final.get("completion_tokens", 0),
            est_usd=final.get("est_usd", 0.0),
        ),
        error=error,
    )
