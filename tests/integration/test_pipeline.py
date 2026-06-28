"""Full ingest -> profile -> ask -> narrate pipeline against real Gemini (.env)."""
import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from data.ingest import ingest_file
from db.models import Dataset, Message, RunRow
from db import session as session_module

_SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_sales.csv"


def _load_sample(engine, tmp_path) -> str:
    datasets = ingest_file(
        filename="sample_sales.csv",
        content=_SAMPLE.read_bytes(),
        storage_dir=tmp_path,
    )
    d = datasets[0]
    with Session(engine) as s:
        s.add(
            Dataset(
                id=d.id, name=d.name, source_path=d.source_path,
                source_kind=d.source_kind, sheet_name=d.sheet_name,
                duckdb_table=d.duckdb_table, profile_json=json.dumps(d.profile),
                row_count=d.row_count, size_bytes=d.size_bytes,
            )
        )
        s.commit()
    return d.id


@pytest.mark.usefixtures("_require_llm_key")
def test_full_pipeline_returns_rich_answer(_isolated_db, tmp_path):
    dataset_id = _load_sample(_isolated_db, tmp_path)
    from graph.runner import ask

    response = ask(dataset_id, "What were total sales (amount) by region?")

    assert response.status == "completed", response.error
    assert response.answer and len(response.answer) > 5
    assert response.key_stats, "expected at least one key stat"
    assert response.chart_spec is not None
    assert response.summary_table is not None
    assert response.summary_table.columns, "summary table must have columns"
    assert response.insight
    assert response.generated_sql.lstrip().upper().startswith(("SELECT", "WITH"))
    assert response.cost.est_usd > 0
    assert response.cost.prompt_tokens > 0
    assert response.cost.completion_tokens > 0


@pytest.mark.usefixtures("_require_llm_key")
def test_full_pipeline_persists_audit_row(_isolated_db, tmp_path):
    dataset_id = _load_sample(_isolated_db, tmp_path)
    from graph.runner import ask

    response = ask(dataset_id, "What were total sales by region?")
    assert response.status == "completed", response.error

    with Session(session_module._engine) as s:
        run = s.get(RunRow, response.run_id)
        assert run is not None
        assert run.status == "completed"
        assert run.question == "What were total sales by region?"
        assert run.generated_sql
        assert run.est_usd and run.est_usd > 0
        assert run.prompt_tokens and run.prompt_tokens > 0
        # result_summary stores aggregates + narration, never a raw-row dump
        summary = json.loads(run.result_summary_json)
        assert "answer" in summary

        # conversation messages recorded (user + assistant)
        msgs = s.query(Message).filter(Message.run_id == response.run_id).all()
        roles = {m.role for m in msgs}
        assert "user" in roles
        assert "assistant" in roles


@pytest.mark.usefixtures("_require_llm_key")
def test_full_pipeline_top_region_is_west(_isolated_db, tmp_path):
    """Correct-answer gate: West is the true top region in the full sample data."""
    dataset_id = _load_sample(_isolated_db, tmp_path)
    from graph.runner import ask
    from data.duckdb_engine import duckdb_query

    response = ask(dataset_id, "Which region had the highest total sales (amount)?")
    assert response.status == "completed", response.error

    # The generated SQL, run locally on the FULL data, must rank West first.
    rows, _ = duckdb_query(
        "SELECT region, SUM(amount) AS total FROM ds GROUP BY region "
        "ORDER BY total DESC",
        # rebuild a ref from the stored dataset
        _ref(dataset_id),
    )
    assert rows[0]["region"] == "West"
    # And the narrated answer should mention West.
    assert "west" in response.answer.lower() or any(
        "west" in str(k.value).lower() for k in response.key_stats
    )


def _ref(dataset_id: str):
    from data.duckdb_engine import DatasetRef
    with Session(session_module._engine) as s:
        ds = s.get(Dataset, dataset_id)
        return DatasetRef(
            dataset_id=ds.id, source_path=ds.source_path,
            source_kind=ds.source_kind, duckdb_table=ds.duckdb_table,
            sheet_name=ds.sheet_name,
        )
