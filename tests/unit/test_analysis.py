"""Profiler + executor unit tests — no LLM key required."""
import numpy as np
import pandas as pd

from analysis.profile import MAX_SAMPLE_ROWS, build_profile
from analysis.execute import execute_pandas


def _frame(n: int = 100) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": (["West", "East", "North", "South"] * (n // 4 + 1))[:n],
            "revenue": np.arange(n, dtype=float),
            "note": [f"row-{i}" for i in range(n)],
        }
    )


def test_profile_sample_capped():
    df = _frame(100)
    profile = build_profile(df)
    assert len(profile["sample"]) <= MAX_SAMPLE_ROWS
    assert profile["row_count"] == 100


def test_profile_shape():
    df = _frame(20)
    profile = build_profile(df)
    names = {c["name"] for c in profile["columns"]}
    assert names == {"region", "revenue", "note"}
    assert "revenue" in profile["numeric_stats"]
    stats = profile["numeric_stats"]["revenue"]
    assert stats["min"] == 0.0
    assert stats["max"] == 19.0


def test_profile_missing_counts():
    df = _frame(10)
    df.loc[0, "region"] = None
    profile = build_profile(df)
    region = next(c for c in profile["columns"] if c["name"] == "region")
    assert region["missing"] == 1


def test_execute_full_data_not_sample():
    df = _frame(1000)
    res = execute_pandas("result = df['revenue'].sum()", df)
    assert res.error is None
    # full-data sum of 0..999
    assert "499500" in res.result_preview


def test_execute_captures_error_not_raises():
    df = _frame(10)
    res = execute_pandas("result = df['does_not_exist'].sum()", df)
    assert res.error is not None
    assert res.result_preview is None


def test_execute_missing_result_is_error():
    df = _frame(10)
    res = execute_pandas("x = 1 + 1", df)
    assert res.error is not None
    assert "result" in res.error


def test_execute_preview_truncated():
    df = _frame(500)
    res = execute_pandas("result = df", df)
    assert res.error is None
    assert "rows total" in res.result_preview  # head-truncated, not full frame
