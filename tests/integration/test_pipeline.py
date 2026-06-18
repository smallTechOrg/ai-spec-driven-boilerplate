"""Integration test: stub run, one session+run record, status=completed."""
import json
import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import data_analyst.db.session as session_module
from data_analyst.db.models import Base, SessionRow, RunRow


@pytest.fixture(autouse=True)
def _stub_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_ANALYST_DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.delenv("DATA_ANALYST_GEMINI_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _use_sqlite(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(session_module, "_engine", engine)
    monkeypatch.setattr(session_module, "_SessionLocal", factory)
    monkeypatch.setattr(session_module, "init_db", lambda: None)
    yield
    engine.dispose()


@pytest.fixture()
def sample_csv(tmp_path) -> str:
    p = tmp_path / "sample.csv"
    p.write_text("name,age,score\nAlice,30,95\nBob,25,82\nCarol,35,88\n")
    return str(p)


@pytest.fixture(autouse=True)
def _reset_llm(monkeypatch):
    import data_analyst.llm.client as llm_module
    monkeypatch.setattr(llm_module, "_provider", None)
    yield
    monkeypatch.setattr(llm_module, "_provider", None)


def test_pipeline_runs_end_to_end(sample_csv):
    from sqlalchemy.orm import Session as OrmSession
    from data_analyst.graph.runner import run_agent
    import uuid

    session_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    with session_module.create_db_session() as db:
        sess_row = SessionRow(
            id=session_id,
            filename="sample.csv",
            file_path=sample_csv,
            file_size_bytes=100,
            row_count=3,
            column_names=json.dumps(["name", "age", "score"]),
            column_dtypes=json.dumps({"name": "object", "age": "int64", "score": "int64"}),
            status="ready",
        )
        db.add(sess_row)
        run_row = RunRow(id=run_id, session_id=session_id)
        db.add(run_row)

    final_state = run_agent(
        session_id=session_id,
        run_id=run_id,
        dataset_path=sample_csv,
        user_question="What does the data look like?",
    )

    assert final_state is not None
    assert final_state.get("error") is None

    with OrmSession(session_module._engine) as db:
        run = db.get(RunRow, run_id)
        assert run is not None
        assert run.status == "completed"
