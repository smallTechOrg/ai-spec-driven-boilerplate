"""Model + storage-layer smoke tests: Run on SQLite, one event on DuckDB."""

from sqlalchemy import select

from src.db.duck import append_event, init_event_store, read_events
from src.db.models import Run


async def test_create_and_read_run(db_session):
    run = Run(input="hello", result="echo: hello")
    db_session.add(run)
    await db_session.commit()

    row = (await db_session.execute(select(Run))).scalar_one()
    assert row.id is not None
    assert row.input == "hello"
    assert row.result == "echo: hello"
    assert row.created_at is not None


def test_duckdb_event_store_write_and_read():
    init_event_store()
    event_id = append_event(kind="test", payload="echo: hi")
    assert isinstance(event_id, int)

    events = read_events(limit=10)
    assert any(e["id"] == event_id and e["payload"] == "echo: hi" for e in events)
