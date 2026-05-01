from __future__ import annotations

from lead_gen_agent.db import repository as repo
from lead_gen_agent.db.session import create_db_session
from lead_gen_agent.graph.runner import run_pipeline


def test_pipeline_end_to_end_with_stub():
    run_id = run_pipeline(country="Germany", industry="Manufacturing", size_band="11-50")
    assert run_id

    with create_db_session() as s:
        runs = repo.list_runs(s)
        assert len(runs) == 1
        assert runs[0].status == "completed"
        assert runs[0].completed_at is not None

        leads = repo.list_leads(s)
        assert len(leads) >= 1  # stub returns 3 candidates
        for l in leads:
            assert 0 <= l.score <= 100
            assert l.rationale
            assert l.country == "Germany"
            assert l.industry == "Manufacturing"
            assert l.size_band == "11-50"
