import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lead_gen_agent.db.models import Base
from lead_gen_agent.db.repository import LeadRepository, SearchRunRepository
from lead_gen_agent.domain import SearchRunCreate, LeadCreate


def _get_db_url() -> str:
    url = os.environ.get("LGA_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("LGA_DATABASE_URL not set")
    return url


@pytest.fixture()
def session():
    engine = create_engine(_get_db_url())
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s
        s.rollback()  # roll back any test mutations


class TestSearchRunRepository:
    def test_create_and_get(self, session):
        repo = SearchRunRepository(session)
        data = SearchRunCreate(country="DE", industry="retail", size_min=10, size_max=50)
        run = repo.create(data)
        session.flush()

        fetched = repo.get(run.id)
        assert fetched is not None
        assert fetched.country == "DE"
        assert fetched.status == "running"

    def test_mark_completed(self, session):
        repo = SearchRunRepository(session)
        run = repo.create(SearchRunCreate(country="FR", industry="finance"))
        session.flush()

        repo.mark_completed(run.id, lead_count=5)
        session.flush()

        updated = repo.get(run.id)
        assert updated.status == "completed"
        assert updated.lead_count == 5
        assert updated.completed_at is not None

    def test_mark_failed(self, session):
        repo = SearchRunRepository(session)
        run = repo.create(SearchRunCreate(country="NL", industry="tech"))
        session.flush()

        repo.mark_failed(run.id, "Gemini quota exceeded")
        session.flush()

        updated = repo.get(run.id)
        assert updated.status == "failed"
        assert updated.error_message == "Gemini quota exceeded"

    def test_list_all_returns_runs(self, session):
        repo = SearchRunRepository(session)
        repo.create(SearchRunCreate(country="ES", industry="logistics"))
        session.flush()
        runs = repo.list_all()
        assert len(runs) >= 1


class TestLeadRepository:
    def _make_run(self, session) -> str:
        repo = SearchRunRepository(session)
        run = repo.create(SearchRunCreate(country="DE", industry="retail"))
        session.flush()
        return run.id

    def test_upsert_inserts_leads(self, session):
        run_id = self._make_run(session)
        repo = LeadRepository(session)
        leads = [
            LeadCreate(
                search_run_id=run_id,
                company_name="Acme GmbH",
                domain="acme.de",
                country="DE",
                industry="retail",
                headcount_estimate="10-50",
                why_fit="Small retailer with no analytics team.",
            )
        ]
        count = repo.upsert_many(leads)
        session.flush()
        assert count == 1

    def test_upsert_dedup_on_domain(self, session):
        run_id = self._make_run(session)
        repo = LeadRepository(session)
        lead = LeadCreate(
            search_run_id=run_id,
            company_name="Beta GmbH",
            domain=f"beta-dedup-{run_id[:8]}.de",
            country="DE",
        )
        first = repo.upsert_many([lead])
        session.flush()
        second = repo.upsert_many([lead])
        session.flush()
        assert first == 1
        assert second == 0

    def test_list_leads_filter(self, session):
        run_id = self._make_run(session)
        repo = LeadRepository(session)
        unique = f"filtertest-{run_id[:8]}.nl"
        repo.upsert_many([
            LeadCreate(search_run_id=run_id, company_name="NL Co", domain=unique, country="NL")
        ])
        session.flush()
        results = repo.list_leads(country="NL")
        assert any(l.domain == unique for l in results)
