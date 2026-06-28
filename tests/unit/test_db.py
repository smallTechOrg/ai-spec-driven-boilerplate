"""DB model tests — no LLM key required."""
from sqlalchemy.orm import Session

from db.models import Dataset, Analysis


def test_dataset_and_analysis_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        ds = Dataset(
            filename="o.csv", storage_path="/tmp/o.csv", row_count=3,
            column_count=2, size_bytes=10, profile={"columns": [], "sample": []},
        )
        s.add(ds)
        s.commit()
        ds_id = ds.id

        a = Analysis(dataset_id=ds_id, question="q?", status="running")
        s.add(a)
        s.commit()
        a_id = a.id

    with Session(_isolated_db) as s:
        a = s.get(Analysis, a_id)
        assert a.dataset_id == ds_id
        assert a.status == "running"
        assert a.steps_taken == 0
