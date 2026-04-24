from __future__ import annotations

from lead_gen_agent.db import repository as repo
from lead_gen_agent.db.session import create_db_session
from lead_gen_agent.domain.models import Lead


def _make_lead(name: str, score: int = 50, country: str = "Germany") -> Lead:
    return Lead(
        name=name,
        website=f"https://{name.lower()}.example",
        country=country,
        industry="Manufacturing",
        size_band="11-50",
        hq_city="Berlin",
        description="Mid-size manufacturer.",
        score=score,
        rationale="No data roles listed; thin tech stack.",
    )


def test_create_and_list_run():
    with create_db_session() as s:
        run_id = repo.create_run(s, {"country": "Germany", "industry": "Manufacturing", "size_band": "11-50"})
        assert run_id
    with create_db_session() as s:
        runs = repo.list_runs(s)
        assert len(runs) == 1
        assert runs[0].id == run_id
        assert runs[0].status == "pending"


def test_add_lead_and_complete_run():
    with create_db_session() as s:
        run_id = repo.create_run(s, {"country": "Germany", "industry": "Retail", "size_band": "51-200"})
    with create_db_session() as s:
        repo.add_lead(s, run_id, _make_lead("Acme", 80))
        repo.add_lead(s, run_id, _make_lead("Zeta", 20))
        repo.complete_run(s, run_id, "completed")
    with create_db_session() as s:
        leads = repo.list_leads(s)
        assert [l.name for l in leads] == ["Acme", "Zeta"]  # ordered by score desc
        runs = repo.list_runs(s)
        assert runs[0].status == "completed"
        assert runs[0].completed_at is not None


def test_list_leads_filters():
    with create_db_session() as s:
        run_id = repo.create_run(s, {})
        repo.add_lead(s, run_id, _make_lead("A", 80, "Germany"))
        repo.add_lead(s, run_id, _make_lead("B", 30, "France"))
        repo.add_lead(s, run_id, _make_lead("C", 90, "Germany"))
    with create_db_session() as s:
        de = repo.list_leads(s, country="Germany")
        assert [l.name for l in de] == ["C", "A"]
        hi = repo.list_leads(s, min_score=85)
        assert [l.name for l in hi] == ["C"]
