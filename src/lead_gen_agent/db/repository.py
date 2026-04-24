"""Repository layer — all DB access goes through here."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from lead_gen_agent.db.models import LeadORM, SearchRunORM
from lead_gen_agent.domain import Lead, LeadCreate, SearchRun, SearchRunCreate


class SearchRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data: SearchRunCreate) -> SearchRun:
        orm = SearchRunORM(
            country=data.country,
            industry=data.industry,
            size_min=data.size_min,
            size_max=data.size_max,
            status="running",
        )
        self._session.add(orm)
        self._session.flush()
        return SearchRun.model_validate(orm)

    def get(self, run_id: str) -> SearchRun | None:
        row = self._session.get(SearchRunORM, run_id)
        return SearchRun.model_validate(row) if row else None

    def list_all(self) -> list[SearchRun]:
        rows = self._session.scalars(
            select(SearchRunORM).order_by(SearchRunORM.created_at.desc())
        ).all()
        return [SearchRun.model_validate(r) for r in rows]

    def mark_completed(self, run_id: str, lead_count: int) -> None:
        row = self._session.get(SearchRunORM, run_id)
        if row:
            row.status = "completed"
            row.lead_count = lead_count
            row.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, run_id: str, error_message: str) -> None:
        row = self._session.get(SearchRunORM, run_id)
        if row:
            row.status = "failed"
            row.error_message = error_message
            row.completed_at = datetime.now(timezone.utc)


class LeadRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(self, leads: list[LeadCreate]) -> int:
        """Insert leads; skip (do nothing) on domain conflict. Returns count inserted."""
        if not leads:
            return 0
        inserted = 0
        for lead in leads:
            stmt = (
                pg_insert(LeadORM)
                .values(
                    company_name=lead.company_name,
                    domain=lead.domain,
                    website=lead.website,
                    country=lead.country,
                    industry=lead.industry,
                    headcount_estimate=lead.headcount_estimate,
                    why_fit=lead.why_fit,
                    status=lead.status,
                    search_run_id=lead.search_run_id,
                )
                .on_conflict_do_nothing(index_elements=["domain"])
            )
            result = self._session.execute(stmt)
            inserted += result.rowcount
        return inserted

    def list_leads(
        self,
        country: str | None = None,
        industry: str | None = None,
        status: str | None = None,
    ) -> list[Lead]:
        q = select(LeadORM).order_by(LeadORM.created_at.desc())
        if country:
            q = q.where(LeadORM.country == country)
        if industry:
            q = q.where(LeadORM.industry.ilike(f"%{industry}%"))
        if status:
            q = q.where(LeadORM.status == status)
        rows = self._session.scalars(q).all()
        return [Lead.model_validate(r) for r in rows]

    def list_by_run(self, run_id: str) -> list[Lead]:
        rows = self._session.scalars(
            select(LeadORM)
            .where(LeadORM.search_run_id == run_id)
            .order_by(LeadORM.created_at.desc())
        ).all()
        return [Lead.model_validate(r) for r in rows]

    def count(self) -> int:
        from sqlalchemy import func
        return self._session.scalar(select(func.count()).select_from(LeadORM)) or 0
