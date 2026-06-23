import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api._common import ok
from db.models import AuditLogEntry
from db.session import get_session
from domain.models import AuditEntry

router = APIRouter()


def _audit_entry(a: AuditLogEntry) -> dict:
    return AuditEntry(
        id=a.id,
        operation=a.operation,
        dataset_id=a.dataset_id,
        query_id=a.query_id,
        sql_text=a.sql_text,
        row_count=a.row_count,
        columns=json.loads(a.columns_json) if a.columns_json else None,
        duration_ms=a.duration_ms,
        success=a.success,
        error_message=a.error_message,
        created_at=a.created_at,
    ).model_dump(mode="json")


@router.get("/audit")
def list_audit(
    dataset_id: str | None = None,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc())
    if dataset_id:
        stmt = stmt.where(AuditLogEntry.dataset_id == dataset_id)
    stmt = stmt.limit(max(1, min(limit, 1000)))
    rows = session.execute(stmt).scalars().all()
    return ok([_audit_entry(a) for a in rows])
