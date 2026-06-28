"""DB layer tests — no LLM key required."""
import json

from sqlalchemy.orm import Session

from db.models import Dataset, Message, RunRow, Session as SessionRow


def test_run_row_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        run = RunRow(question="What were total sales?", dataset_id="ds1")
        s.add(run)
        s.commit()
        run_id = run.id

    with Session(_isolated_db) as s:
        fetched = s.get(RunRow, run_id)
        assert fetched is not None
        assert fetched.question == "What were total sales?"
        assert fetched.dataset_id == "ds1"
        assert fetched.status == "pending"
        assert fetched.result_summary_json is None


def test_run_row_audit_fields_persist(_isolated_db):
    with Session(_isolated_db) as s:
        run = RunRow(
            question="q",
            status="completed",
            plan_json=json.dumps(["step 1"]),
            generated_sql="SELECT 1",
            result_summary_json=json.dumps({"answer": "ok"}),
            prompt_tokens=812,
            completion_tokens=240,
            est_usd=0.00042,
        )
        s.add(run)
        s.commit()
        run_id = run.id

    with Session(_isolated_db) as s:
        run = s.get(RunRow, run_id)
        assert run.prompt_tokens == 812
        assert run.completion_tokens == 240
        assert run.est_usd == 0.00042
        assert json.loads(run.plan_json) == ["step 1"]


def test_dataset_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        ds = Dataset(
            name="sample.csv",
            source_path="/tmp/sample.csv",
            source_kind="csv",
            duckdb_table="ds",
            row_count=480,
            profile_json=json.dumps({"row_count": 480, "columns": []}),
        )
        s.add(ds)
        s.commit()
        ds_id = ds.id

    with Session(_isolated_db) as s:
        ds = s.get(Dataset, ds_id)
        assert ds.name == "sample.csv"
        assert ds.row_count == 480
        assert ds.sheet_name is None


def test_message_and_session_tables_exist(_isolated_db):
    with Session(_isolated_db) as s:
        sess = SessionRow(active_dataset_id="ds1")
        s.add(sess)
        s.flush()
        msg = Message(role="user", content="hi", dataset_id="ds1", session_id=sess.id)
        s.add(msg)
        s.commit()
        msg_id = msg.id

    with Session(_isolated_db) as s:
        msg = s.get(Message, msg_id)
        assert msg.role == "user"
        assert msg.content == "hi"
