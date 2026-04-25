"""Repository — all database read/write operations for the sourcing agent."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from sourcing_agent.db.models import MaterialLineItem, SourcingRun, SupplierRecommendation
from sourcing_agent.domain.models import (
    MaterialRequest,
    SourcingRunStatus,
    SupplierCandidateData,
)


# ─── SourcingRun ────────────────────────────────────────────────────────────


def create_run(session: Session, project_name: str, materials: list[MaterialRequest]) -> SourcingRun:
    run = SourcingRun(
        id=uuid.uuid4(),
        project_name=project_name,
        status=SourcingRunStatus.PENDING,
    )
    session.add(run)
    session.flush()

    for mat in materials:
        item = MaterialLineItem(
            id=uuid.uuid4(),
            run_id=run.id,
            material_name=mat.name,
            quantity=Decimal(str(mat.quantity)),
            unit=mat.unit,
        )
        session.add(item)

    session.flush()
    return run


def get_run(session: Session, run_id: uuid.UUID) -> SourcingRun | None:
    return session.get(SourcingRun, run_id)


def get_run_with_details(session: Session, run_id: uuid.UUID) -> SourcingRun | None:
    run = session.get(SourcingRun, run_id)
    if run is not None:
        # Eagerly load relationships
        _ = run.line_items
        for item in run.line_items:
            _ = item.recommendations
    return run


def update_run_status(
    session: Session,
    run_id: uuid.UUID,
    status: str,
    error_message: str | None = None,
) -> None:
    run = session.get(SourcingRun, run_id)
    if run is None:
        return
    run.status = status
    if status in (SourcingRunStatus.COMPLETED, SourcingRunStatus.FAILED):
        run.completed_at = datetime.now(timezone.utc)
    if error_message is not None:
        run.error_message = error_message
    session.flush()


# ─── SupplierRecommendation ──────────────────────────────────────────────────


def save_recommendations(
    session: Session,
    run_id: uuid.UUID,
    line_item_id: uuid.UUID,
    candidates: list[SupplierCandidateData],
) -> list[SupplierRecommendation]:
    rows = []
    for rank, candidate in enumerate(candidates, start=1):
        rec = SupplierRecommendation(
            id=uuid.uuid4(),
            run_id=run_id,
            line_item_id=line_item_id,
            rank=rank,
            supplier_name=candidate.supplier_name,
            supplier_location=candidate.supplier_location,
            price_per_unit=Decimal(str(candidate.price_per_unit)),
            currency=candidate.currency,
            lead_time_days=candidate.lead_time_days,
            certifications=", ".join(candidate.certifications) if candidate.certifications else None,
            score=Decimal(str(round(candidate.score, 4))),
            notes=candidate.notes,
        )
        session.add(rec)
        rows.append(rec)
    session.flush()
    return rows
