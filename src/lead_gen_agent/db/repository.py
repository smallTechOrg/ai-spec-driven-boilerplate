from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from lead_gen_agent.db.models import LeadRow, RunRow
from lead_gen_agent.domain.models import Lead, Run


def create_run(session: Session, filters: dict) -> str:
    row = RunRow(filters=filters, status="pending")
    session.add(row)
    session.flush()
    return row.id


def complete_run(session: Session, run_id: str, status: str, error: str | None = None) -> None:
    row = session.get(RunRow, run_id)
    if row is None:
        return
    row.status = status
    row.error_message = error
    row.completed_at = datetime.now(timezone.utc)


def add_lead(session: Session, run_id: str, lead: Lead) -> str:
    row = LeadRow(
        run_id=run_id,
        name=lead.name,
        website=lead.website,
        country=lead.country,
        industry=lead.industry,
        size_band=lead.size_band,
        hq_city=lead.hq_city,
        description=lead.description,
        score=lead.score,
        rationale=lead.rationale,
    )
    session.add(row)
    session.flush()
    return row.id


def list_runs(session: Session) -> list[Run]:
    rows = session.execute(
        select(RunRow).order_by(RunRow.created_at.desc())
    ).scalars().all()
    return [
        Run(
            id=r.id,
            filters=r.filters,
            status=r.status,
            error_message=r.error_message,
            created_at=r.created_at,
            completed_at=r.completed_at,
        )
        for r in rows
    ]


def list_leads(
    session: Session,
    country: str | None = None,
    industry: str | None = None,
    size_band: str | None = None,
    min_score: int | None = None,
) -> list[Lead]:
    stmt = select(LeadRow).order_by(LeadRow.score.desc(), LeadRow.created_at.desc())
    if country:
        stmt = stmt.where(LeadRow.country == country)
    if industry:
        stmt = stmt.where(LeadRow.industry == industry)
    if size_band:
        stmt = stmt.where(LeadRow.size_band == size_band)
    if min_score is not None:
        stmt = stmt.where(LeadRow.score >= min_score)
    rows = session.execute(stmt).scalars().all()
    return [
        Lead(
            id=r.id,
            run_id=r.run_id,
            name=r.name,
            website=r.website,
            country=r.country,
            industry=r.industry,
            size_band=r.size_band,
            hq_city=r.hq_city,
            description=r.description,
            score=r.score,
            rationale=r.rationale,
            created_at=r.created_at,
        )
        for r in rows
    ]
