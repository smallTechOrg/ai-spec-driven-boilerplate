"""Privacy invariant: raw rows never reach the LLM (architecture-critical).

Runs the REAL agent against a multi-thousand-row CSV with a sentinel value that
exists ONLY in rows far beyond the <=5-row sample window, then asserts:
  1. the profile sample is <= MAX_SAMPLE_ROWS rows;
  2. no prompt sent to the LLM client contains the sentinel value;
  3. no prompt contains more rows than the sample window.
"""
import json

import pytest

from analysis.profile import MAX_SAMPLE_ROWS, build_profile, load_csv
from db.models import DatasetRow
from db.session import create_db_session
from graph.runner import run_agent

from tests.phase1.conftest import SENTINEL_NOTE


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


def test_profile_sample_capped(big_csv):
    df = load_csv(str(big_csv))
    profile = build_profile(df)
    assert len(profile["sample"]) <= MAX_SAMPLE_ROWS


@pytest.mark.usefixtures("_require_llm_key")
def test_no_raw_rows_reach_llm(big_csv, llm_spy):
    dataset_id = _register_dataset(big_csv)

    payload = run_agent(dataset_id, "What is the total revenue by region?")
    assert payload["status"] == "completed"

    # The spy captured every prompt actually sent to Gemini.
    assert len(llm_spy) > 0, "expected real LLM calls to have been captured"

    for call in llm_spy:
        blob = (call["prompt"] or "") + "\n" + (call["system"] or "")
        # The sentinel exists only in a deep raw row (not a top-5 categorical,
        # not a numeric extremum). If it appears in any prompt, a raw row leaked.
        assert SENTINEL_NOTE not in blob, "a deep raw-row value leaked to the LLM"

    # Defensive row-count proxy: the unique 'note' values per row would each
    # produce a "note" key if a row block were serialized; the only allowed
    # row-level data is the <=5-row sample, so 'row-' note markers (which only
    # appear in bulk rows, never in the first-5 'intro-' sample) must be absent.
    for call in llm_spy:
        blob = (call["prompt"] or "")
        assert "row-" not in blob, "bulk raw rows appear to have leaked to the LLM"
