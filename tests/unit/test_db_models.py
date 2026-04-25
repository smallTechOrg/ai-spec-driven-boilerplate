from __future__ import annotations

from sourcing_agent.db.models import (
    RecommendationRow,
    RunRow,
    SourcingRequestRow,
    SupplierRow,
)


def test_request_run_supplier_recommendation_roundtrip(db_session):
    req = SourcingRequestRow(
        material="red clay brick",
        quantity="10000 units",
        location="Bangalore",
        budget="₹70,000",
        timeline="2 weeks",
        criteria="prefer ISI-marked, MOQ flexible",
    )
    db_session.add(req)
    db_session.flush()

    run = RunRow(
        request_id=req.id,
        status="completed",
        llm_provider="stub",
        search_provider="stub",
    )
    db_session.add(run)
    db_session.flush()

    sup = SupplierRow(
        run_id=run.id,
        name="Acme Bricks Pvt Ltd",
        location="Bangalore",
        price_indication="₹6.50 / brick",
        lead_time="5–7 days",
        source_url="https://example.com/acme",
        notes="ISI-marked; MOQ 5000",
    )
    db_session.add(sup)
    db_session.flush()

    rec = RecommendationRow(
        run_id=run.id,
        supplier_id=sup.id,
        rank=1,
        score=87,
        rationale="Best match on price + ISI quality + Bangalore delivery.",
    )
    db_session.add(rec)
    db_session.commit()

    fetched_run = db_session.get(RunRow, run.id)
    assert fetched_run is not None
    assert fetched_run.status == "completed"
    assert len(fetched_run.suppliers) == 1
    assert len(fetched_run.recommendations) == 1
    assert fetched_run.recommendations[0].score == 87
    assert fetched_run.suppliers[0].name == "Acme Bricks Pvt Ltd"


def test_request_to_runs_relationship(db_session):
    req = SourcingRequestRow(
        material="OPC 53 cement",
        quantity="200 bags",
        location="Mumbai",
    )
    db_session.add(req)
    db_session.flush()

    for _ in range(3):
        db_session.add(
            RunRow(
                request_id=req.id,
                llm_provider="stub",
                search_provider="stub",
            )
        )
    db_session.commit()

    fetched = db_session.get(SourcingRequestRow, req.id)
    assert len(fetched.runs) == 3
