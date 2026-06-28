"""Profiler unit tests — no LLM key required."""
import pytest

from analyst.profile import compute_profile, profile_csv, MAX_SAMPLE_ROWS


def test_profile_basic(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("a,b\n1,x\n2,y\n3,z\n")
    prof = profile_csv(str(p))
    assert prof.row_count == 3
    names = [c["name"] for c in prof.schema]
    assert names == ["a", "b"]
    assert len(prof.sample_rows) == 3


def test_profile_caps_sample(tmp_path):
    rows = "\n".join(str(i) for i in range(50))
    p = tmp_path / "big.csv"
    p.write_text("n\n" + rows + "\n")
    prof = profile_csv(str(p))
    assert prof.row_count == 50
    assert len(prof.sample_rows) == MAX_SAMPLE_ROWS


def test_profile_empty_file_raises(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("")
    with pytest.raises(ValueError):
        profile_csv(str(p))


def test_profile_handles_nan(tmp_path):
    p = tmp_path / "n.csv"
    p.write_text("a,b\n1,\n,2\n")
    prof = profile_csv(str(p))
    # NaN must serialize to None (JSON-safe)
    assert prof.sample_rows[0]["b"] is None


# --- Phase 2: full auto-profile (compute_profile) ---------------------------

def _by_name(profile, name):
    return next(c for c in profile if c["name"] == name)


def test_compute_profile_per_column_shape(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("price,status,when\n10,a,2024-01-01\n20,b,2024-02-01\n,a,\n")
    profile = compute_profile(str(p))
    assert [c["name"] for c in profile] == ["price", "status", "when"]
    for col in profile:
        for key in ("name", "dtype", "type_category", "missing", "distinct",
                    "min", "max", "examples"):
            assert key in col


def test_compute_profile_numeric_range_and_missing(tmp_path):
    p = tmp_path / "p.csv"
    # A real missing value: an empty cell on a populated row (id column keeps the row).
    p.write_text("id,price\n1,10\n2,20\n3,30\n4,\n")
    price = _by_name(compute_profile(str(p)), "price")
    assert price["type_category"] == "numeric"
    assert price["missing"] == 1
    assert price["distinct"] == 3
    assert price["min"] == 10
    assert price["max"] == 30


def test_compute_profile_categorical_no_range(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("id,status\n1,delivered\n2,shipped\n3,delivered\n4,\n")
    status = _by_name(compute_profile(str(p)), "status")
    assert status["type_category"] == "categorical"
    assert status["missing"] == 1
    assert status["distinct"] == 2
    assert status["min"] is None and status["max"] is None
    assert "delivered" in status["examples"]
    assert len(status["examples"]) <= 5


def test_compute_profile_datetime_range(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("ts\n2024-01-01 10:00:00\n2024-03-01 09:00:00\n2024-02-01 08:00:00\n")
    ts = _by_name(compute_profile(str(p)), "ts")
    assert ts["type_category"] == "datetime"
    assert ts["min"] is not None and ts["max"] is not None
    assert str(ts["min"]) < str(ts["max"])


def test_compute_profile_empty_file_raises(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("")
    with pytest.raises(ValueError):
        compute_profile(str(p))
