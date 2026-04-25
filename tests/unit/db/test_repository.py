"""Unit tests for the database repository layer."""

import uuid
from decimal import Decimal

import pytest

from sourcing_agent.db.models import SourcingRun
from sourcing_agent.db.repository import (
    create_run,
    get_run,
    get_run_with_details,
    save_recommendations,
    update_run_status,
)
from sourcing_agent.domain.models import MaterialRequest, SourcingRunStatus, SupplierCandidateData


def test_create_run_persists_run_and_items(db_session):
    SessionLocal = db_session
    with SessionLocal() as session:
        materials = [
            MaterialRequest(name="Portland Cement", quantity=500, unit="bags"),
            MaterialRequest(name="Clay Bricks", quantity=10000, unit="units"),
        ]
        run = create_run(session, "Test Project", materials)
        run_id = run.id
        session.commit()

    with SessionLocal() as session:
        loaded = get_run_with_details(session, run_id)
        assert loaded is not None
        assert loaded.project_name == "Test Project"
        assert loaded.status == SourcingRunStatus.PENDING
        assert len(loaded.line_items) == 2
        names = {item.material_name for item in loaded.line_items}
        assert names == {"Portland Cement", "Clay Bricks"}


def test_update_run_status(db_session):
    SessionLocal = db_session
    with SessionLocal() as session:
        run = create_run(session, "Status Test", [MaterialRequest(name="Sand", quantity=10, unit="tonnes")])
        run_id = run.id
        session.commit()

    with SessionLocal() as session:
        update_run_status(session, run_id, SourcingRunStatus.RUNNING)
        session.commit()

    with SessionLocal() as session:
        run = get_run(session, run_id)
        assert run.status == SourcingRunStatus.RUNNING

    with SessionLocal() as session:
        update_run_status(session, run_id, SourcingRunStatus.COMPLETED)
        session.commit()

    with SessionLocal() as session:
        run = get_run(session, run_id)
        assert run.status == SourcingRunStatus.COMPLETED
        assert run.completed_at is not None


def test_save_recommendations(db_session):
    SessionLocal = db_session
    with SessionLocal() as session:
        run = create_run(session, "Recs Test", [MaterialRequest(name="Steel", quantity=5, unit="tonnes")])
        run_id = run.id
        line_item = run.line_items[0]
        line_item_id = line_item.id

        candidates = [
            SupplierCandidateData(
                supplier_name="SteelCo",
                supplier_location="Pittsburgh, PA",
                price_per_unit=800.0,
                lead_time_days=10,
                certifications=["ISO 9001"],
                score=0.85,
            ),
            SupplierCandidateData(
                supplier_name="MetalWorks",
                supplier_location="Cleveland, OH",
                price_per_unit=750.0,
                lead_time_days=14,
                certifications=[],
                score=0.72,
            ),
        ]
        save_recommendations(session, run_id, line_item_id, candidates)
        session.commit()

    with SessionLocal() as session:
        run = get_run_with_details(session, run_id)
        recs = sorted(run.recommendations, key=lambda r: r.rank)
        assert len(recs) == 2
        assert recs[0].rank == 1
        assert recs[0].supplier_name == "SteelCo"
        assert recs[1].supplier_name == "MetalWorks"
        assert float(recs[0].score) == pytest.approx(0.85, abs=0.001)


def test_get_run_returns_none_for_missing(db_session):
    SessionLocal = db_session
    with SessionLocal() as session:
        result = get_run(session, uuid.uuid4())
        assert result is None
