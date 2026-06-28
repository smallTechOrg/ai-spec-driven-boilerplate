"""DB layer tests for the Phase-1 analysis schema — no LLM key required."""
from sqlalchemy.orm import Session

from db.models import DatasetRow, ConversationRow, MessageRow, RunRow


def test_dataset_row_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        ds = DatasetRow(
            name="sales.csv",
            file_path="uploads/x/sales.csv",
            file_type="csv",
            size_bytes=100,
            row_count=10,
            profile_json='{"columns": []}',
        )
        s.add(ds)
        s.commit()
        ds_id = ds.id

    with Session(_isolated_db) as s:
        fetched = s.get(DatasetRow, ds_id)
        assert fetched is not None
        assert fetched.name == "sales.csv"
        assert fetched.file_type == "csv"
        assert fetched.row_count == 10


def test_run_row_defaults_and_update(_isolated_db):
    with Session(_isolated_db) as s:
        run = RunRow(dataset_id="d1", question="total revenue?")
        s.add(run)
        s.commit()
        run_id = run.id
        assert run.status == "pending"

    with Session(_isolated_db) as s:
        run = s.get(RunRow, run_id)
        run.status = "completed"
        run.answer = "the answer"
        run.code = "result = df.sum()"
        run.iterations = 1
        s.commit()

    with Session(_isolated_db) as s:
        run = s.get(RunRow, run_id)
        assert run.status == "completed"
        assert run.answer == "the answer"
        assert run.iterations == 1


def test_conversation_and_messages(_isolated_db):
    with Session(_isolated_db) as s:
        conv = ConversationRow(dataset_id="d1")
        s.add(conv)
        s.commit()
        conv_id = conv.id
        s.add(MessageRow(conversation_id=conv_id, role="user", content="hi"))
        s.add(MessageRow(conversation_id=conv_id, role="assistant", content="hello"))
        s.commit()

    with Session(_isolated_db) as s:
        msgs = (
            s.query(MessageRow)
            .filter(MessageRow.conversation_id == conv_id)
            .order_by(MessageRow.created_at.asc())
            .all()
        )
        assert [m.role for m in msgs] == ["user", "assistant"]
