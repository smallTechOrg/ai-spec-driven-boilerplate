import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from data_analysis_agent.db.models import Base, DatasetRow, QueryRecordRow, AgentRunRow


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_create_dataset(db):
    ds = DatasetRow(filename="data.csv", file_path="/tmp/data.csv")
    db.add(ds)
    db.commit()
    assert ds.id is not None
    assert ds.filename == "data.csv"


def test_dataset_column_names(db):
    ds = DatasetRow(filename="data.csv", file_path="/tmp/data.csv")
    ds.column_names = ["a", "b", "c"]
    db.add(ds)
    db.commit()
    db.refresh(ds)
    assert ds.column_names == ["a", "b", "c"]


def test_create_query_record(db):
    ds = DatasetRow(filename="data.csv", file_path="/tmp/data.csv")
    db.add(ds)
    db.flush()
    qr = QueryRecordRow(dataset_id=ds.id, question="What is the average?")
    db.add(qr)
    db.commit()
    assert qr.id is not None
    assert qr.status == "pending"


def test_create_agent_run(db):
    ds = DatasetRow(filename="data.csv", file_path="/tmp/data.csv")
    db.add(ds)
    db.flush()
    qr = QueryRecordRow(dataset_id=ds.id, question="Q")
    db.add(qr)
    db.flush()
    run = AgentRunRow(query_record_id=qr.id)
    db.add(run)
    db.commit()
    assert run.id is not None
    assert run.status == "pending"
