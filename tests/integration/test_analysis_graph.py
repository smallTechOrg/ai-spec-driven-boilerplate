"""Integration tests for the analysis-graph slice — REAL Gemini key (loads .env).

Exercises the LLM-plan -> local-execute -> LLM-explain loop end to end over the
`tests/fixtures/sales.csv` fixture (region, amount, date, units). These are real
LLM calls; they are skipped only if no provider key is configured.

Known fixture facts (hand-computed):
  * total amount                       = 4180.0
  * group-by region mean amount        = West 105, East 232.5, North 280, South 427.5
  * region with highest average amount = "South"
"""
import shutil
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from db import session as session_module
from db.models import DatasetRow, QueryRow
from graph.runner import run_query
from tools import sandbox
from tools.dataset import load_and_describe, load_dataframe

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "sales.csv"
_TOTAL_AMOUNT = 4180.0
_TOLERANCE = 1e-6


def _is_close(got: float, expected: float) -> bool:
    return abs(float(got) - expected) <= _TOLERANCE * max(1.0, abs(expected))


def _seed_dataset(tmp_path) -> str:
    """Upload-equivalent: copy the fixture into data/uploads/<id>.csv and persist
    a DatasetRow pointing at it (so run_query can resolve the file path)."""
    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)

    described = load_and_describe(str(_FIXTURE))
    with Session(session_module._engine) as s:
        row = DatasetRow(
            filename="sales.csv",
            source_format="csv",
            file_path="",  # set below once we know the id
            row_count=described["row_count"],
            schema_json=described["schema"],
            sample_json=described["sample"],
            size_bytes=_FIXTURE.stat().st_size,
        )
        s.add(row)
        s.flush()
        dataset_id = row.id
        dest = uploads / f"{dataset_id}.csv"
        shutil.copyfile(_FIXTURE, dest)
        row.file_path = str(dest)
        s.commit()
    return dataset_id


@pytest.mark.usefixtures("_require_llm_key")
def test_total_amount_aggregation(_isolated_db, tmp_path):
    dataset_id = _seed_dataset(tmp_path)

    result = run_query(dataset_id, "What is the total amount?")

    assert result["status"] == "completed", result
    # answer / explanation / code all present
    assert result["answer"], "answer must be non-empty"
    assert result["explanation"], "explanation must be non-empty"
    assert result["code"], "code must be non-empty"
    assert "df" in result["code"], "code must reference the dataframe"

    # The numeric result equals the hand-computed sum within tolerance.
    numeric = float(result["result"])
    assert _is_close(numeric, _TOTAL_AMOUNT), f"got {numeric}, expected {_TOTAL_AMOUNT}"

    # Re-running the returned code over the fixture df reproduces the same number.
    df = load_dataframe(str(_FIXTURE))
    rerun = sandbox.run(result["code"], df)
    assert rerun["ok"], rerun
    assert _is_close(float(rerun["result"]), _TOTAL_AMOUNT)

    # The auditable QueryRow was persisted.
    with Session(session_module._engine) as s:
        persisted = s.get(QueryRow, result["query_id"])
    assert persisted is not None
    assert persisted.status == "completed"
    assert persisted.dataset_id == dataset_id
    assert persisted.code
    assert persisted.model  # which real model answered


@pytest.mark.usefixtures("_require_llm_key")
def test_groupby_ranking(_isolated_db, tmp_path):
    dataset_id = _seed_dataset(tmp_path)

    result = run_query(dataset_id, "Which region has the highest average amount?")

    assert result["status"] == "completed", result
    assert result["answer"]
    assert result["explanation"]
    assert result["code"]

    # The result should resolve to "South" (West105/East232.5/North280/South427.5).
    assert "South" in str(result["result"]) or "South" in result["answer"], result


@pytest.mark.usefixtures("_require_llm_key")
def test_empty_question_fails_gracefully(_isolated_db, tmp_path):
    """An empty question is rejected by guard_input -> handle_error with a
    human-readable error, status=failed, and a persisted QueryRow (no crash)."""
    dataset_id = _seed_dataset(tmp_path)

    result = run_query(dataset_id, "   ")

    assert result["status"] == "failed", result
    err = result.get("error") or ""
    assert err  # human-readable
    assert "Traceback" not in err and '  File "' not in err

    with Session(session_module._engine) as s:
        persisted = s.get(QueryRow, result["query_id"])
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.error_message


def test_malformed_csv_fails_gracefully(_isolated_db, tmp_path):
    """A dataset whose file is not a readable CSV must fail gracefully in
    load_dataset -> handle_error: status=failed, human-readable error, no crash
    or stack trace, and a persisted QueryRow. (No LLM call is needed.)"""
    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    bad = uploads / "broken.csv"
    bad.write_bytes(b"")  # empty file -> pandas EmptyDataError -> human-readable ValueError

    with Session(session_module._engine) as s:
        row = DatasetRow(
            filename="broken.csv", source_format="csv", file_path=str(bad),
            row_count=0, schema_json=[], sample_json={}, size_bytes=bad.stat().st_size,
        )
        s.add(row)
        s.flush()
        dataset_id = row.id
        s.commit()

    result = run_query(dataset_id, "What is the total amount?")

    assert result["status"] == "failed", result
    err = result.get("error") or ""
    assert err  # human-readable
    assert "Traceback" not in err and '  File "' not in err

    with Session(session_module._engine) as s:
        persisted = s.get(QueryRow, result["query_id"])
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.error_message
