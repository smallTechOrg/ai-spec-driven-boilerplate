"""Profiling is local and correct — no LLM key required."""
import pandas as pd

from analysis.profile import profile_dataframe, profile_file, kind_for_filename


def _write_csv(tmp_path):
    df = pd.DataFrame(
        {
            "region": ["North", "South", "North", "East"],
            "revenue": [100, 250, 175, 300],
            "units": [10, 25, 17, 30],
        }
    )
    path = tmp_path / "sales.csv"
    df.to_csv(path, index=False)
    return path


def test_profile_columns_dtypes_rowcount(tmp_path):
    path = _write_csv(tmp_path)
    profile = profile_file(str(path), kind="csv")

    assert profile["row_count"] == 4
    assert profile["column_count"] == 3
    names = [c["name"] for c in profile["columns"]]
    assert names == ["region", "revenue", "units"]

    by_name = {c["name"]: c for c in profile["columns"]}
    # pandas 3.x reports "str"; older reports "object" — accept either
    assert by_name["region"]["dtype"] in ("object", "str")
    assert by_name["region"]["n_unique"] == 3
    assert "int" in by_name["revenue"]["dtype"]
    # numeric ranges captured
    assert by_name["revenue"]["min"] == 100
    assert by_name["revenue"]["max"] == 300
    # sample values are bounded metadata, present for the categorical column
    assert "North" in by_name["region"]["sample_values"]


def test_profile_is_jsonable(tmp_path):
    import json

    path = _write_csv(tmp_path)
    profile = profile_file(str(path), kind="csv")
    # must round-trip through JSON (persisted as JSON in the DB)
    json.dumps(profile)


def test_kind_for_filename():
    assert kind_for_filename("a.csv") == "csv"
    assert kind_for_filename("b.xlsx") == "xlsx"
    assert kind_for_filename("c.txt") is None


def test_profile_xlsx(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    path = tmp_path / "data.xlsx"
    df.to_excel(path, index=False, engine="openpyxl")
    profile = profile_file(str(path), kind="xlsx")
    assert profile["row_count"] == 3
    assert [c["name"] for c in profile["columns"]] == ["a", "b"]
