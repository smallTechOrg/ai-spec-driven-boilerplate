"""End-to-end real agent run against a multi-thousand-row CSV.

Asserts the answer matches a pandas ground-truth computed in the test, that
plan + code are present, and that the run row persisted with status=completed.
The fixture is large enough that a <=5-row sample would give an observably
different answer than the full file — proving full-data computation.
"""
import json

import pytest

from analysis.profile import build_profile, load_csv
from db.models import DatasetRow, RunRow
from db.session import create_db_session
from graph.runner import run_agent


def _register_dataset(csv_path) -> str:
    df = load_csv(str(csv_path))
    profile = build_profile(df)
    with create_db_session() as session:
        ds = DatasetRow(
            name="sales.csv",
            file_path=str(csv_path),
            file_type="csv",
            size_bytes=csv_path.stat().st_size,
            row_count=len(df),
            profile_json=json.dumps(profile, default=str),
        )
        session.add(ds)
        session.flush()
        return ds.id


@pytest.mark.usefixtures("_require_llm_key")
def test_total_revenue_by_region_full_data(big_csv):
    # Ground truth over the FULL file.
    df = load_csv(str(big_csv))
    truth = df.groupby("region")["revenue"].sum()
    west_total = int(truth["West"])      # 5*1 + 1000*10 = 10005
    east_total = int(truth["East"])      # 1000*10 = 10000
    assert west_total != east_total      # sanity: distinguishable

    # A <=5-row sample (all West, revenue 1) would total West=5, no East — so a
    # sampled answer is observably different from the full-data answer.
    assert west_total > 5

    dataset_id = _register_dataset(big_csv)
    payload = run_agent(dataset_id, "What is the total revenue for each region?")

    assert payload["status"] == "completed"
    assert payload["plan"], "plan should be present"
    assert payload["code"], "generated code should be present"
    answer = payload["answer"] or ""
    preview = payload["result_preview"] or ""

    # The full-data per-region totals must be reflected in the answer/preview.
    haystack = answer + "\n" + preview
    assert str(west_total) in haystack or "10,005" in haystack
    assert str(east_total) in haystack or "10,000" in haystack

    # Run row persisted.
    with create_db_session() as session:
        run = session.get(RunRow, payload["run_id"])
        assert run is not None
        assert run.status == "completed"
        assert run.code
        assert run.plan
        assert run.answer
