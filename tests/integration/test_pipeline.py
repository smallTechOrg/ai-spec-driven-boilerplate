from __future__ import annotations

from sourcing_agent.db.models import (
    RecommendationRow,
    RunRow,
    SourcingRequestRow,
    SupplierRow,
)


def test_pipeline_runs_end_to_end_in_stub_mode(db_session):
    from sourcing_agent.graph.runner import run_agent

    req = SourcingRequestRow(
        material="red clay brick",
        quantity="10000 units",
        location="Bangalore",
        budget="₹70,000",
        timeline="2 weeks",
        criteria="ISI-marked preferred",
    )
    db_session.add(req)
    db_session.commit()
    request_id = req.id

    run_id = run_agent(request_id)
    db_session.expire_all()

    run = db_session.get(RunRow, run_id)
    assert run is not None
    assert run.status == "completed"
    assert run.llm_provider == "stub"
    assert run.search_provider == "stub"

    suppliers = db_session.query(SupplierRow).filter_by(run_id=run_id).all()
    assert len(suppliers) >= 3
    s0 = suppliers[0]
    assert s0.google_rating is not None and 0 <= s0.google_rating <= 5
    assert s0.google_review_count is not None
    assert s0.feedback_summary and len(s0.feedback_summary) > 30
    assert s0.delivery_reliability
    assert s0.solvency_signal
    assert s0.gst_registered is not None
    assert s0.years_in_business is not None

    recs = (
        db_session.query(RecommendationRow)
        .filter_by(run_id=run_id)
        .order_by(RecommendationRow.rank)
        .all()
    )
    assert len(recs) >= 3
    assert recs[0].rank == 1
    assert 0 <= recs[0].score <= 100
    assert len(recs[0].rationale) > 50
