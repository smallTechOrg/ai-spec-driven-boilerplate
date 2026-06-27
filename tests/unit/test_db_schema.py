"""Schema round-trip for the analysis tables: DatasetRow + QueryRow."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, DatasetRow, QueryRow


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/schema.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sess = factory()
    yield sess
    sess.close()
    engine.dispose()


def test_dataset_and_query_round_trip(session):
    schema = [
        {"name": "region", "dtype": "object"},
        {"name": "sales", "dtype": "int64"},
    ]
    sample = {
        "preview_rows": [{"region": "north", "sales": 10}],
        "summary": {"sales": {"min": 10, "max": 90, "mean": 50.0}},
    }
    ds = DatasetRow(
        id="sales_2024",
        filename="sales_2024.csv",
        source_format="csv",
        file_path="data/uploads/sales_2024.csv",
        row_count=3,
        schema_json=schema,
        sample_json=sample,
        size_bytes=2048,
    )
    session.add(ds)
    session.commit()

    result = {"value": 150, "unit": "rows"}
    q = QueryRow(
        id="q1",
        dataset_id="sales_2024",
        conversation_id="sales_2024",
        question="What is the total sales?",
        code="df['sales'].sum()",
        result_json=result,
        explanation="Summed the sales column across all rows.",
        answer="Total sales is 150.",
        status="completed",
        error_message=None,
        repair_attempts=1,
        tokens_in=120,
        tokens_out=45,
        cost_usd=0.0003,
        latency_ms=812.5,
        model="gemini-2.5-flash",
        node_trace={"plan": 100, "execute": 200},
        guard_code="OK",
    )
    session.add(q)
    session.commit()

    # Re-read from the DB.
    session.expire_all()
    got_ds = session.get(DatasetRow, "sales_2024")
    assert got_ds is not None
    assert got_ds.filename == "sales_2024.csv"
    assert got_ds.source_format == "csv"
    assert got_ds.file_path == "data/uploads/sales_2024.csv"
    assert got_ds.row_count == 3
    assert got_ds.size_bytes == 2048
    assert got_ds.schema_json == schema
    assert got_ds.sample_json == sample
    assert got_ds.sample_json["summary"]["sales"]["max"] == 90
    assert got_ds.created_at is not None

    got_q = session.get(QueryRow, "q1")
    assert got_q is not None
    assert got_q.dataset_id == "sales_2024"
    assert got_q.conversation_id == "sales_2024"
    assert got_q.question == "What is the total sales?"
    assert got_q.code == "df['sales'].sum()"
    assert got_q.result_json == result
    assert got_q.result_json["value"] == 150
    assert got_q.explanation == "Summed the sales column across all rows."
    assert got_q.answer == "Total sales is 150."
    assert got_q.status == "completed"
    assert got_q.error_message is None
    assert got_q.repair_attempts == 1
    assert got_q.tokens_in == 120
    assert got_q.tokens_out == 45
    assert got_q.cost_usd == pytest.approx(0.0003)
    assert got_q.latency_ms == pytest.approx(812.5)
    assert got_q.model == "gemini-2.5-flash"
    assert got_q.node_trace == {"plan": 100, "execute": 200}
    assert got_q.guard_code == "OK"
    assert got_q.created_at is not None


def test_query_defaults_and_failure_row(session):
    ds = DatasetRow(
        id="d2",
        filename="d2.csv",
        file_path="data/uploads/d2.csv",
        row_count=1,
        schema_json=[{"name": "x", "dtype": "int64"}],
        sample_json={"preview_rows": [], "summary": {}},
        size_bytes=10,
    )
    session.add(ds)
    session.commit()

    q = QueryRow(
        id="q2",
        dataset_id="d2",
        question="Broken question",
        status="failed",
        error_message="Could not compute the answer.",
    )
    session.add(q)
    session.commit()
    session.expire_all()

    got = session.get(QueryRow, "q2")
    assert got.status == "failed"
    assert got.error_message == "Could not compute the answer."
    assert got.conversation_id == ""          # column default
    assert got.repair_attempts == 0           # column default
    assert got.code is None
    assert got.result_json is None
    assert got.answer is None

    # FK default on the dataset.
    assert session.get(DatasetRow, "d2").source_format == "csv"
