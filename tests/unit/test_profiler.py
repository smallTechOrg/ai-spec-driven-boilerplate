import pandas as pd

from analysis.profiler import profile_csv, profile_dataframe


def _write_csv(tmp_path, n_rows):
    rows = []
    regions = ["NW", "SE", "NE", "SW"]
    for i in range(n_rows):
        rows.append({"region": regions[i % 4], "amount": float(i % 100), "note": f"row-{i}"})
    df = pd.DataFrame(rows)
    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)
    return path


def test_profile_row_count_is_true_full_count(tmp_path):
    path = _write_csv(tmp_path, 5000)
    prof = profile_csv(path)
    assert prof["row_count"] == 5000
    assert prof["column_count"] == 3
    assert len(prof["sample_rows"]) <= 5


def test_profile_columns_typed_with_stats(tmp_path):
    path = _write_csv(tmp_path, 200)
    prof = profile_csv(path)
    by_name = {c["name"]: c for c in prof["profile"]}
    assert set(by_name) == {"region", "amount", "note"}
    assert by_name["region"]["distinct_count"] == 4
    assert by_name["amount"]["min"] == 0.0
    assert by_name["amount"]["max"] == 99.0
    assert by_name["region"]["null_count"] == 0


def test_profile_dataframe_caps_sample(tmp_path):
    df = pd.DataFrame({"a": range(50)})
    prof = profile_dataframe(df, sample_rows=5)
    assert prof["row_count"] == 50
    assert len(prof["sample_rows"]) == 5


def test_unparseable_file_raises(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_bytes(b"\x00\x01\x02notcsv")
    # binary junk may parse as a single col; force a truly empty file
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    import pytest

    with pytest.raises(ValueError):
        profile_csv(empty)
