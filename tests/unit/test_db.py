"""DB layer tests — no LLM key required."""
from sqlalchemy.orm import Session
from db.models import RunRow
import db.session as session_module


def test_run_row_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        run = RunRow(input_text="hello world")
        s.add(run)
        s.commit()
        run_id = run.id

    with Session(_isolated_db) as s:
        fetched = s.get(RunRow, run_id)
        assert fetched is not None
        assert fetched.input_text == "hello world"
        assert fetched.status == "pending"
        assert fetched.output_text is None


def test_run_row_status_update(_isolated_db):
    with Session(_isolated_db) as s:
        run = RunRow(input_text="test")
        s.add(run)
        s.commit()
        run_id = run.id

    with Session(_isolated_db) as s:
        run = s.get(RunRow, run_id)
        run.status = "completed"
        run.output_text = "some output"
        s.commit()

    with Session(_isolated_db) as s:
        run = s.get(RunRow, run_id)
        assert run.status == "completed"
        assert run.output_text == "some output"


def test_multiple_runs_independent(_isolated_db):
    ids = []
    with Session(_isolated_db) as s:
        for i in range(3):
            run = RunRow(input_text=f"input {i}")
            s.add(run)
        s.commit()
        # fetch all
        runs = s.query(RunRow).all()
        ids = [r.id for r in runs]

    assert len(ids) == 3
    assert len(set(ids)) == 3  # all unique
