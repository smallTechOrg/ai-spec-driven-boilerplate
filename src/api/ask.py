"""`POST /ask` — run a session-scoped analysis (Phase 3).

Phase-3 scope (the full `spec/api.md` `/ask` contract):

- Every `/ask` belongs to a *session*. An explicit `session_id` resumes a
  conversation (enforcing the 20-turn cap and inheriting / matching its
  datasets); without one, a fresh `ConversationSessionRow` is created scoped to
  the resolved datasets.
- Dataset resolution: explicit `dataset_id`/`dataset_ids` (each validated),
  else inherit from the session, else hand ALL uploaded dataset ids to the
  runner and let the C19 selector choose (the `run_selector` path).
- Multi-turn: prior completed turns of the session are assembled into
  `conversation_history` and passed to the runner.
- Pre-flight clarification (C26): unless `skip_clarification`, the runner may
  short-circuit and return `type:"clarification"` — we relay that payload and
  the runner owns the thin `query_runs` row it created.
- Answer path: the full answer payload, with `answer_html` rendered from the
  Markdown, the real `session_id`, suggestions, selector reasoning, and prompt
  breakdown.

Run-row creation is owned by `run_agent` (it has been since Phase 2) — this
route never duplicates it.
"""
from __future__ import annotations

from datetime import datetime, timezone

from markdown_it import MarkdownIt
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.models import ConversationSessionRow, DatasetRow, QueryRunRow
from db.session import get_session
from domain.ask import AskRequest
from graph.runner import run_agent

router = APIRouter()

_md = MarkdownIt()

# A session is capped at 20 settled turns (spec/roadmap.md "Conversation cap").
_TURN_LIMIT = 20

# Statuses that count as a settled turn against the cap / for history assembly.
_TURN_STATUSES = ("completed", "failed", "clarification")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_explicit_dataset_ids(req: AskRequest) -> list[str]:
    """Dataset ids the caller explicitly named, from `dataset_ids` or `dataset_id`."""
    if req.dataset_ids:
        return [d for d in req.dataset_ids if d]
    if req.dataset_id:
        return [req.dataset_id]
    return []


def _session_datasets(row: ConversationSessionRow) -> list[str]:
    if row.dataset_ids_json:
        return [d for d in row.dataset_ids_json if d]
    if row.dataset_id:
        return [row.dataset_id]
    return []


def _count_turns(session: Session, session_id: str) -> int:
    return session.execute(
        select(func.count())
        .select_from(QueryRunRow)
        .where(QueryRunRow.session_id == session_id)
        .where(QueryRunRow.status.in_(_TURN_STATUSES))
    ).scalar_one()


def _conversation_history(session: Session, session_id: str) -> list[dict]:
    """Prior COMPLETED turns of the session, oldest-first, as {question, answer}."""
    rows = (
        session.execute(
            select(QueryRunRow)
            .where(QueryRunRow.session_id == session_id)
            .where(QueryRunRow.status == "completed")
            .order_by(QueryRunRow.created_at.asc())
        )
        .scalars()
        .all()
    )
    return [{"question": r.question, "answer": r.answer or ""} for r in rows]


@router.post("/ask")
def ask(req: AskRequest, session: Session = Depends(get_session)) -> dict:
    question = (req.question or "").strip()
    if not question:
        raise api_error("empty_question", "Question must not be empty.", 400)

    explicit_ids = _resolve_explicit_dataset_ids(req)

    # An explicit dataset that does not exist is a 404 (more specific than the
    # global "no datasets" guard) — validate every named id.
    for dataset_id in explicit_ids:
        if session.get(DatasetRow, dataset_id) is None:
            raise api_error("not_found", f"Dataset {dataset_id} not found", 404)

    # --- Session resolution ------------------------------------------------
    session_row: ConversationSessionRow | None = None
    if req.session_id:
        session_row = session.get(ConversationSessionRow, req.session_id)
        if session_row is None:
            raise api_error("not_found", f"Session {req.session_id} not found", 404)

        # 20-turn cap.
        if _count_turns(session, session_row.id) >= _TURN_LIMIT:
            raise api_error(
                "turn_limit", "Session has reached the 20-turn limit.", 400
            )

        session_datasets = _session_datasets(session_row)
        if explicit_ids:
            # Explicit datasets must be a subset of the session's datasets.
            if session_datasets and set(explicit_ids) - set(session_datasets):
                raise api_error(
                    "session_mismatch",
                    "The requested datasets do not match this session.",
                    400,
                )
            resolved_ids = explicit_ids
        else:
            # Inherit the session's datasets when none are passed.
            resolved_ids = session_datasets
        run_selector = False
    else:
        if explicit_ids:
            resolved_ids = explicit_ids
            run_selector = False
        else:
            # No explicit datasets and no session -> the C19 selector path: hand
            # ALL uploaded dataset ids to the runner and let pre-flight choose.
            all_ids = (
                session.execute(select(DatasetRow.id)).scalars().all()
            )
            if not all_ids:
                raise api_error(
                    "no_datasets",
                    "No datasets uploaded yet. Upload a file first.",
                    400,
                )
            resolved_ids = list(all_ids)
            run_selector = True

    # Guard: a session that ended up with no datasets (and no explicit / selector
    # candidates) cannot proceed.
    if not resolved_ids:
        all_count = session.execute(
            select(func.count()).select_from(DatasetRow)
        ).scalar_one()
        if all_count == 0:
            raise api_error(
                "no_datasets", "No datasets uploaded yet. Upload a file first.", 400
            )
        raise api_error("no_datasets", "Specify a dataset to ask about.", 400)

    # --- Ensure a session exists for this turn ----------------------------
    if session_row is None:
        session_row = ConversationSessionRow(
            dataset_id=resolved_ids[0] if resolved_ids else None,
            dataset_ids_json=list(resolved_ids),
            name=None,
        )
        session.add(session_row)
        session.flush()  # assign the id before we hand it to the runner
    session_id = session_row.id

    # --- Multi-turn history (prior completed turns) -----------------------
    history = _conversation_history(session, session_id)

    # Release this request's write transaction BEFORE invoking the runner.
    # `run_agent` opens its own connection to insert/update the `query_runs`
    # row; under SQLite a still-open write lock here would deadlock that write
    # ("database is locked"). Committing the session row first frees the lock
    # and durably persists the session even if the run later fails.
    session.commit()

    # --- Run the agent (run-row creation lives in run_agent) --------------
    result = run_agent(
        question,
        resolved_ids,
        session_id=session_id,
        conversation_history=history,
        skip_clarification=req.skip_clarification,
        run_selector=run_selector,
        max_iterations=None,
    )

    # Bump the session's recency so the sidebar orders by last activity. The
    # row was committed/expired above; re-load it in this session to update.
    session_row = session.get(ConversationSessionRow, session_id)
    if session_row is not None:
        session_row.updated_at = _now()

    # --- Clarification short-circuit (C26) --------------------------------
    if result.get("type") == "clarification":
        return ok(
            {
                "type": "clarification",
                "clarification_question": result.get("clarification_question"),
                "run_id": result["run_id"],
                "session_id": session_id,
                "status": "clarification",
            }
        )

    # --- Answer path ------------------------------------------------------
    answer_markdown = result.get("answer") or ""
    answer_html = _md.render(answer_markdown) if answer_markdown else ""
    # The runner returns the FINAL resolved/selected ids — prefer them.
    datasets_used = result.get("dataset_ids") or resolved_ids

    return ok(
        {
            "type": "answer",
            "run_id": result["run_id"],
            "session_id": session_id,
            "dataset_ids": datasets_used,
            "derived_dataset_ids": result.get("derived_dataset_ids", []),
            "datasets_used": datasets_used,
            "selector_reasoning": result.get("selector_reasoning"),
            "answer_markdown": answer_markdown,
            "answer_html": answer_html,
            "iteration_count": result.get("iteration_count", 0),
            "tokens_input": result.get("tokens_input", 0),
            "tokens_output": result.get("tokens_output", 0),
            "status": result.get("status", "completed"),
            "is_best_effort": result.get("is_best_effort", False),
            "steps": result.get("action_history") or [],
            "suggested_questions": result.get("suggested_questions") or [],
            "prompt_breakdown": result.get("prompt_breakdown") or {},
        }
    )
