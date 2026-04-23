from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from prmonitor.db.models import DBRun
from prmonitor.domain.models import Run

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _to_domain(row: DBRun) -> Run:
    return Run(id=row.id, ran_at=row.ran_at, status=row.status,
               stale_pr_count=row.stale_pr_count, error_message=row.error_message)

async def create_run(session: AsyncSession) -> Run:
    row = DBRun(ran_at=_now(), status="running", stale_pr_count=0)
    session.add(row)
    await session.flush()
    return _to_domain(row)

async def update_run(session: AsyncSession, run_id: int, **fields: object) -> Run | None:
    result = await session.execute(select(DBRun).where(DBRun.id == run_id))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        setattr(row, k, v)
    await session.flush()
    return _to_domain(row)

async def get_runs(session: AsyncSession) -> list[Run]:
    result = await session.execute(select(DBRun).order_by(DBRun.ran_at.desc()))
    return [_to_domain(r) for r in result.scalars()]
