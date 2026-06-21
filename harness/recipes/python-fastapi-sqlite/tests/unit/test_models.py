from sqlalchemy import select

from src.db.models import Run


async def test_create_and_read_run(db_session):
    run = Run(input="hello", result=None)
    db_session.add(run)
    await db_session.commit()

    row = (await db_session.execute(select(Run))).scalar_one()
    assert row.id is not None
    assert row.input == "hello"
    assert row.result is None
    assert row.created_at is not None
