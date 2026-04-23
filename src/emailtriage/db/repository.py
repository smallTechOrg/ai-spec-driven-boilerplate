from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from emailtriage.db.models import DBEmailResult, DBRun
from emailtriage.domain.models import EmailResult, Run

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _run(row: DBRun) -> Run:
    return Run(id=row.id, ran_at=row.ran_at, status=row.status,
               emails_processed=row.emails_processed, error_message=row.error_message)

def _result(row: DBEmailResult) -> EmailResult:
    return EmailResult(id=row.id, email_id=row.email_id, subject=row.subject,
                       sender=row.sender, classification=row.classification,
                       draft_reply=row.draft_reply, processed_at=row.processed_at)

async def create_run(session: AsyncSession) -> Run:
    row = DBRun(ran_at=_now(), status="running", emails_processed=0)
    session.add(row)
    await session.flush()
    return _run(row)

async def update_run(session: AsyncSession, run_id: int, **fields: object) -> None:
    result = await session.execute(select(DBRun).where(DBRun.id == run_id))
    row = result.scalar_one_or_none()
    if row:
        for k, v in fields.items():
            setattr(row, k, v)
        await session.flush()

async def save_result(session: AsyncSession, result: EmailResult) -> EmailResult:
    row = DBEmailResult(email_id=result.email_id, subject=result.subject,
                        sender=result.sender, classification=result.classification,
                        draft_reply=result.draft_reply, processed_at=result.processed_at)
    session.add(row)
    await session.flush()
    return _result(row)

async def get_results_for_run_era(session: AsyncSession) -> list[EmailResult]:
    rows = await session.execute(select(DBEmailResult).order_by(DBEmailResult.processed_at.desc()))
    return [_result(r) for r in rows.scalars()]
