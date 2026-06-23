"""DB layer tests — no LLM key required."""
from sqlalchemy.orm import Session

from db.models import AuditLogEntry, Dataset, Query


def test_dataset_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        ds = Dataset(
            name="sales.csv",
            table_name="ds_abc",
            row_count=3,
            columns_json='[{"name": "region", "type": "TEXT"}]',
            schema_text="TABLE ds_abc (region TEXT)",
            sample_text="region\nWest",
        )
        s.add(ds)
        s.commit()
        ds_id = ds.id

    with Session(_isolated_db) as s:
        fetched = s.get(Dataset, ds_id)
        assert fetched is not None
        assert fetched.name == "sales.csv"
        assert fetched.row_count == 3
        assert fetched.created_at is not None


def test_query_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        q = Query(dataset_id="ds-1", question="how many?", status="pending")
        s.add(q)
        s.commit()
        q_id = q.id

    with Session(_isolated_db) as s:
        q = s.get(Query, q_id)
        q.status = "completed"
        q.answer_text = "There are 3."
        q.generated_sql = "SELECT COUNT(*) FROM ds_abc"
        s.commit()

    with Session(_isolated_db) as s:
        q = s.get(Query, q_id)
        assert q.status == "completed"
        assert q.answer_text == "There are 3."


def test_audit_entry_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        a = AuditLogEntry(
            operation="ingest",
            dataset_id="ds-1",
            sql_text="CREATE TABLE ds_abc",
            row_count=3,
            duration_ms=12,
            success=True,
        )
        s.add(a)
        s.commit()
        a_id = a.id

    with Session(_isolated_db) as s:
        a = s.get(AuditLogEntry, a_id)
        assert a.operation == "ingest"
        assert a.success is True
        assert a.duration_ms == 12
