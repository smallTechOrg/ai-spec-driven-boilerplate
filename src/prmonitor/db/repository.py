from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from prmonitor.db.models import DBRun
from prmonitor.domain.models import Run

def _now(): return datetime.now(timezone.utc)
def _to_domain(r: DBRun): return Run(id=r.id, ran_at=r.ran_at, status=r.status, stale_pr_count=r.stale_pr_count, error_message=r.error_message)

async def create_run(session: AsyncSession) -> Run:
    row = DBRun(ran_at=_now(), status="running", stale_pr_count=0)
    session.add(row); await session.flush()
    return _to_domain(row)

async def update_run(session: AsyncSession, run_id: int, **fields) -> None:
    r = (await session.execute(select(DBRun).where(DBRun.id == run_id))).scalar_one_or_none()
    if r:
        for k, v in fields.items(): setattr(r, k, v)
        await session.flush()

async def get_runs(session: AsyncSession) -> list[Run]:
    rows = await session.execute(select(DBRun).order_by(DBRun.ran_at.desc()))
    return [_to_domain(r) for r in rows.scalars()]
