"""Profiler shape tests — no LLM key required."""
import pandas as pd

from analysis.profile import build_profile
from tests.fixtures.data import write_simple_csv


def test_profile_reports_columns_types_ranges_and_missing(tmp_path):
    path = write_simple_csv(tmp_path / "simple.csv")
    df = pd.read_csv(path)

    profile = build_profile(df, sample_rows=3)

    cols = {c["name"]: c for c in profile["columns"]}
    assert set(cols) == {"region", "order_value", "qty"}

    # Numeric column: range + mean + missing
    ov = cols["order_value"]
    assert ov["missing_count"] == 1
    assert ov["min"] == 50.0
    assert ov["max"] == 200.0
    assert "mean" in ov

    # String column: top_values + missing + distinct
    region = cols["region"]
    assert region["dtype"] == "string"
    assert region["missing_count"] == 1
    assert region["distinct_count"] == 3
    assert "West" in region["top_values"]


def test_profile_sample_is_bounded(tmp_path):
    path = write_simple_csv(tmp_path / "simple.csv")
    df = pd.read_csv(path)
    profile = build_profile(df, sample_rows=2)
    assert len(profile["sample"]) == 2
