"""Unit tests for the SQLAlchemy models — persistence + relationships + cascade."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from datachat.db.models import Conversation, Dataset, File, Message, Run


@pytest.mark.asyncio
async def test_dataset_with_file_persists(db_session):
    ds = Dataset(name="Q1 Sales")
    ds.files.append(
        File(
            filename="sales.csv",
            duckdb_table="ds_x_sales",
            schema_json=[{"name": "region", "type": "VARCHAR"}],
            sample_rows_json=[["west"], ["east"]],
            row_count=2,
        )
    )
    db_session.add(ds)
    await db_session.commit()

    loaded = (await db_session.execute(select(Dataset))).scalar_one()
    assert loaded.name == "Q1 Sales"
    assert len(loaded.files) == 1
    assert loaded.files[0].row_count == 2


@pytest.mark.asyncio
async def test_conversation_messages_and_run(db_session):
    ds = Dataset(name="ds")
    conv = Conversation(dataset=ds, title="first")
    run = Run(conversation=conv, status="completed", iteration_count=2)
    conv.messages.append(Message(role="user", content="how many rows?"))
    conv.messages.append(
        Message(
            role="assistant",
            content="There are 2 rows.",
            run_id=run.id,
            result_table_json={"columns": ["n"], "rows": [[2]]},
            trace_json=[{"description": "Counted rows.", "action": "SELECT count(*)", "result": "2", "is_error": False}],
        )
    )
    db_session.add_all([ds, conv, run])
    await db_session.commit()

    loaded = (await db_session.execute(select(Conversation))).scalar_one()
    assert len(loaded.messages) == 2
    roles = {m.role for m in loaded.messages}
    assert roles == {"user", "assistant"}
    assistant = next(m for m in loaded.messages if m.role == "assistant")
    assert assistant.result_table_json["rows"] == [[2]]


@pytest.mark.asyncio
async def test_deleting_dataset_cascades(db_session):
    ds = Dataset(name="ds")
    ds.conversations.append(Conversation())
    ds.files.append(
        File(
            filename="a.csv",
            duckdb_table="t",
            schema_json=[],
            sample_rows_json=[],
            row_count=0,
        )
    )
    db_session.add(ds)
    await db_session.commit()

    await db_session.delete(ds)
    await db_session.commit()

    assert (await db_session.execute(select(File))).first() is None
    assert (await db_session.execute(select(Conversation))).first() is None
