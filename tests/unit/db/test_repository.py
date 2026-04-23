import pytest
from emailtriage.db.repository import create_run, update_run, save_result
from emailtriage.domain.models import EmailResult
from datetime import datetime, timezone

async def test_create_run(db_session):
    run = await create_run(db_session)
    assert run.id is not None
    assert run.status == "running"

async def test_update_run(db_session):
    run = await create_run(db_session)
    await update_run(db_session, run.id, status="completed", emails_processed=5)
    # verify via a second query
    from sqlalchemy import select
    from emailtriage.db.models import DBRun
    row = (await db_session.execute(select(DBRun).where(DBRun.id == run.id))).scalar_one()
    assert row.status == "completed"
    assert row.emails_processed == 5

async def test_save_result(db_session):
    result = EmailResult(email_id="abc123", subject="Hello", sender="a@b.com",
                         classification="urgent", draft_reply="Hi there",
                         processed_at=datetime.now(timezone.utc))
    saved = await save_result(db_session, result)
    assert saved.id is not None
    assert saved.classification == "urgent"
