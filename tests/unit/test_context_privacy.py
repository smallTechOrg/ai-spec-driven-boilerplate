"""The privacy boundary is the defining constraint — assert it is airtight.

The LLM payload built by the single chokepoint must contain ONLY the profile,
a <=5-row sample, the question and history — NEVER the full row set.
"""

import json

import pandas as pd

from analysis.profiler import profile_dataframe
from llm.context import MAX_SAMPLE_ROWS, build_llm_context


def _big_df(n=5000):
    return pd.DataFrame(
        {
            "region": [["NW", "SE", "NE", "SW"][i % 4] for i in range(n)],
            "amount": [float(i) for i in range(n)],
            "secret_marker": [f"ROW_SECRET_{i}" for i in range(n)],
        }
    )


def test_payload_excludes_full_row_set_for_5000_rows():
    df = _big_df(5000)
    prof = profile_dataframe(df, sample_rows=5)
    assert prof["row_count"] == 5000  # true full count, not sampled

    payload = build_llm_context(
        question="how many rows per region?",
        profile=prof["profile"],
        sample_rows=prof["sample_rows"],
        history=[],
        row_count=prof["row_count"],
    )

    # The serialised payload must NOT contain rows beyond the sample.
    # Sample is rows 0-4 -> ROW_SECRET_0..4 may appear; nothing from row 5+ may.
    assert "ROW_SECRET_4999" not in payload
    assert "ROW_SECRET_2500" not in payload
    assert "ROW_SECRET_5" not in payload

    parsed = json.loads(payload)
    assert len(parsed["dataset"]["sample_rows"]) <= MAX_SAMPLE_ROWS
    assert parsed["dataset"]["row_count"] == 5000
    # profile carries stats, not the values
    assert isinstance(parsed["dataset"]["profile"], list)


def test_sample_is_capped_even_if_more_rows_passed():
    rows = [{"x": i} for i in range(100)]
    payload = build_llm_context(
        question="q",
        profile=[{"name": "x", "dtype": "int64"}],
        sample_rows=rows,
        row_count=100,
    )
    parsed = json.loads(payload)
    assert len(parsed["dataset"]["sample_rows"]) == MAX_SAMPLE_ROWS


def test_history_is_truncated():
    history = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(20)]
    payload = build_llm_context(
        question="latest",
        profile=[],
        sample_rows=[],
        history=history,
        row_count=0,
    )
    parsed = json.loads(payload)
    assert len(parsed["history"]) <= 6
    # most recent kept
    assert parsed["history"][-1]["question"] == "q19"


def test_history_is_injected_into_payload_for_follow_ups():
    """Follow-up context: prior turns must actually reach the LLM payload so a
    question like 'now only for region NW' can be resolved against them.
    """
    history = [{"question": "How many rows per region?", "answer": "NW 300, SE 2500"}]
    payload = build_llm_context(
        question="now only for region NW",
        profile=[{"name": "region", "dtype": "object"}],
        sample_rows=[],
        history=history,
        row_count=7000,
    )
    parsed = json.loads(payload)
    assert parsed["history"], "history must be injected for follow-up resolution"
    assert parsed["history"][-1]["question"] == "How many rows per region?"
    assert parsed["history"][-1]["answer"] == "NW 300, SE 2500"
    # And it is present in the raw serialised string actually sent to Gemini.
    assert "How many rows per region?" in payload
