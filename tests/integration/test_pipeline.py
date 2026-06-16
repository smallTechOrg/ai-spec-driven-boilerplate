"""Integration test: stubbed pipeline runs end-to-end with no OpenRouter key."""
import csv
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import data_analysis_agent.db.session as session_module
from data_analysis_agent.db.models import Base, DatasetRow, QueryRecordRow, AgentRunRow


@pytest.fixture(autouse=True)
def _stub_env(monkeypatch):
    monkeypatch.setenv("DATAANALYSIS_DATABASE_URL", "sqlite:///stub_test.db")
    monkeypatch.delenv("DATAANALYSIS_OPENROUTER_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _use_sqlite(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(session_module, "_engine", engine)
    monkeypatch.setattr(session_module, "_SessionLocal", factory)
    monkeypatch.setattr(session_module, "init_db", lambda: None)

    yield

    engine.dispose()
    monkeypatch.setattr(session_module, "_engine", None)
    monkeypatch.setattr(session_module, "_SessionLocal", None)


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "sample.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["region", "sales", "units"])
        writer.writerow(["North", 10000, 50])
        writer.writerow(["South", 8000, 40])
        writer.writerow(["East", 12000, 60])
    return str(path)


@pytest.fixture
def dataset_and_query(csv_file):
    with session_module.create_db_session() as session:
        ds = DatasetRow(filename="sample.csv", file_path=csv_file)
        session.add(ds)
        session.flush()
        qr = QueryRecordRow(dataset_id=ds.id, question="What is the total sales?")
        session.add(qr)
        session.flush()
        return ds.id, qr.id, csv_file


def test_pipeline_runs_end_to_end(dataset_and_query):
    from data_analysis_agent.graph.runner import run_pipeline

    # Reset LLM client singleton so stub is used
    import data_analysis_agent.llm.client as llm_module
    llm_module._client = None

    dataset_id, query_record_id, csv_path = dataset_and_query
    final_state = run_pipeline(
        query_record_id=query_record_id,
        dataset_id=dataset_id,
        question="What is the total sales?",
        csv_path=csv_path,
    )

    assert final_state.get("error") is None

    with Session(session_module._engine) as s:
        qr = s.get(QueryRecordRow, query_record_id)
        assert qr is not None
        assert qr.status == "completed"
        assert qr.answer is not None
        assert len(qr.answer) > 0

        runs = s.query(AgentRunRow).filter_by(query_record_id=query_record_id).all()
        assert len(runs) == 1
        assert runs[0].status == "completed"
