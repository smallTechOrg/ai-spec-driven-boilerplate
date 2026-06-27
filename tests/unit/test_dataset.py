"""Unit tests for the local dataset tool (src/tools/dataset.py).

These run against a real CSV fixture (tests/fixtures/sales.csv) — no LLM, no DB,
no mocks. Hand-computed expected values are asserted directly.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from tools import dataset

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sales.csv"

# Hand-computed from tests/fixtures/sales.csv (16 rows, 4 regions).
EXPECTED_ROW_COUNT = 16
EXPECTED_AMOUNT_SUM = 4180.0
EXPECTED_AMOUNT_MEAN = 261.25
EXPECTED_AMOUNT_MIN = 50.0
EXPECTED_AMOUNT_MAX = 500.0


def test_load_dataframe_reads_fixture():
    df = dataset.load_dataframe(str(FIXTURE))
    assert len(df) == EXPECTED_ROW_COUNT
    assert list(df.columns) == ["region", "amount", "date", "units"]
    # Real data, real arithmetic — total sum is a distinct, checkable answer.
    assert df["amount"].sum() == pytest.approx(EXPECTED_AMOUNT_SUM)


def test_derive_schema_dtypes():
    df = dataset.load_dataframe(str(FIXTURE))
    schema = dataset.derive_schema(df)

    by_name = {col["name"]: col["dtype"] for col in schema}
    assert set(by_name) == {"region", "amount", "date", "units"}
    # amount is a float column, units an integer column.
    assert by_name["amount"].startswith("float")
    assert by_name["units"].startswith("int")
    # region is non-numeric (object/str depending on pandas version).
    assert not by_name["region"].startswith(("float", "int"))


def test_derive_sample_preview_is_bounded():
    df = dataset.load_dataframe(str(FIXTURE))
    sample_rows = 5
    sample = dataset.derive_sample(df, sample_rows)

    preview = sample["preview_rows"]
    # Bounded strictly to sample_rows even though the fixture has more rows.
    assert len(preview) == sample_rows
    assert sample_rows < EXPECTED_ROW_COUNT
    # Each preview row is a JSON-safe dict over the columns.
    assert preview[0]["region"] == "West"
    assert preview[0]["amount"] == pytest.approx(100.0)


def test_preview_rows_are_json_safe():
    import json

    df = dataset.load_dataframe(str(FIXTURE))
    sample = dataset.derive_sample(df, 20)
    # Must round-trip through JSON without a custom encoder.
    json.dumps(sample)


def test_summary_numeric_stats_match_hand_computed():
    df = dataset.load_dataframe(str(FIXTURE))
    sample = dataset.derive_sample(df, 20)
    amount = sample["summary"]["amount"]

    assert amount["count"] == EXPECTED_ROW_COUNT
    assert amount["null_count"] == 0
    assert amount["min"] == pytest.approx(EXPECTED_AMOUNT_MIN)
    assert amount["max"] == pytest.approx(EXPECTED_AMOUNT_MAX)
    assert amount["mean"] == pytest.approx(EXPECTED_AMOUNT_MEAN)


def test_summary_object_column_has_top_categories():
    df = dataset.load_dataframe(str(FIXTURE))
    sample = dataset.derive_sample(df, 20)
    region = sample["summary"]["region"]

    assert "top_categories" in region
    assert region["count"] == EXPECTED_ROW_COUNT
    cats = {c["value"]: c["count"] for c in region["top_categories"]}
    # At least 3 distinct regions present; each appears 4 times in the fixture.
    assert {"West", "East", "North", "South"} <= set(cats)
    assert cats["West"] == 4


def test_load_and_describe_returns_full_bundle():
    bundle = dataset.load_and_describe(str(FIXTURE), sample_rows=20)
    assert bundle["row_count"] == EXPECTED_ROW_COUNT
    assert len(bundle["schema"]) == 4
    assert "preview_rows" in bundle["sample"]
    assert "summary" in bundle["sample"]
    # df is returned for immediate caller use (execute_code reloads it itself).
    assert len(bundle["df"]) == EXPECTED_ROW_COUNT


def test_garbage_file_raises_clear_error(tmp_path):
    bad = tmp_path / "not_a_csv.bin"
    # Binary noise with embedded NULs — not parseable as CSV.
    bad.write_bytes(b"\x00\x01\x02\xff\xfe garbage \x00 not,csv\x00\x01")
    with pytest.raises(ValueError, match="Could not read this file as a CSV"):
        dataset.load_dataframe(str(bad))


def test_missing_file_raises_clear_error(tmp_path):
    missing = tmp_path / "nope.csv"
    with pytest.raises(ValueError, match="Could not read this file as a CSV"):
        dataset.load_dataframe(str(missing))


def test_oversized_file_rejected(tmp_path, monkeypatch):
    from config.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_mb", 0)  # everything is "too big"

    big = tmp_path / "big.csv"
    big.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="exceeds"):
        dataset.load_dataframe(str(big))


def test_too_many_rows_rejected(tmp_path, monkeypatch):
    from config.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_rows", 2)

    rows = "n\n" + "\n".join(str(i) for i in range(10)) + "\n"
    f = tmp_path / "many.csv"
    f.write_text(rows)
    with pytest.raises(ValueError, match="row limit"):
        dataset.load_dataframe(str(f))
