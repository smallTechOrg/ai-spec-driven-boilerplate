"""Local executor runs generated-style code over ALL rows, not the sample."""

import pandas as pd

from analysis.executor import execute_code


def _write_csv(tmp_path, n_rows=5000):
    regions = ["NW", "SE", "NE", "SW"]
    df = pd.DataFrame(
        {"region": [regions[i % 4] for i in range(n_rows)], "amount": [float(i) for i in range(n_rows)]}
    )
    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)
    return path


def _write_skewed_csv(tmp_path):
    """Engineer a fixture where the 200-row truncation != full-data counts.

    The first 200 rows are ALL "NW"; the true full-data distribution is very
    different. A sample/truncation-based answer would report NW dominating; the
    correct full-data answer must report the real per-region totals.
    """
    rows = ["NW"] * 300 + ["SE"] * 2500 + ["SW"] * 2700 + ["NE"] * 1500
    df = pd.DataFrame({"region": rows, "amount": [float(i) for i in range(len(rows))]})
    path = tmp_path / "skewed.csv"
    df.to_csv(path, index=False)
    # True full-data counts, computed directly with pandas.
    expected = df.groupby("region").size().to_dict()
    return path, expected, len(rows)


def test_executes_over_all_rows(tmp_path):
    path = _write_csv(tmp_path, 5000)
    code = "result = df.groupby('region').size().reset_index(name='count')"
    out = execute_code(code, path)
    assert out["traceback"] is None
    table = out["result_table"]
    counts = {r["region"]: r["count"] for r in table["rows"]}
    # 5000 rows split evenly across 4 regions -> 1250 each (NOT a 5-row sample)
    assert sum(counts.values()) == 5000
    assert counts["NW"] == 1250


def test_total_count_matches_full_file(tmp_path):
    path = _write_csv(tmp_path, 5000)
    out = execute_code("result = len(df)", path)
    assert out["traceback"] is None
    assert out["result_table"]["rows"][0]["value"] == 5000


def test_duckdb_path(tmp_path):
    path = _write_csv(tmp_path, 5000)
    code = "result = con.execute('SELECT region, COUNT(*) AS count FROM df GROUP BY region').df()"
    out = execute_code(code, path)
    assert out["traceback"] is None
    assert sum(r["count"] for r in out["result_table"]["rows"]) == 5000


def test_failure_returns_clean_traceback(tmp_path):
    path = _write_csv(tmp_path, 10)
    out = execute_code("result = df['nonexistent_column'].sum()", path)
    assert out["result_table"] is None
    assert out["traceback"] is not None
    assert "nonexistent_column" in out["traceback"] or "KeyError" in out["traceback"]


def test_dangerous_code_rejected(tmp_path):
    path = _write_csv(tmp_path, 10)
    out = execute_code("import os\nresult = os.listdir('.')", path)
    assert out["result_table"] is None
    assert out["traceback"] is not None


# --------------------------------------------------------------------------- #
# BLOCKER 1 regression: bare trailing expression must be captured as result,
# over the FULL dataset — and a no-result generation must error cleanly.
# --------------------------------------------------------------------------- #

def test_bare_expression_groupby_with_reset_index_full_data(tmp_path):
    """`df.groupby(...).size().reset_index(name='count')` with NO `result =`."""
    path, expected, total = _write_skewed_csv(tmp_path)
    code = "df.groupby('region').size().reset_index(name='count')"
    out = execute_code(code, path)
    assert out["traceback"] is None, out["traceback"]
    table = out["result_table"]
    counts = {r["region"]: r["count"] for r in table["rows"]}
    # TRUE full-data counts (NOT the 200-row truncation, which is all-NW).
    assert counts == expected
    assert sum(counts.values()) == total
    # The first 200 rows are all NW; a truncation-based answer would say NW=200.
    assert counts["NW"] == expected["NW"]


def test_bare_expression_groupby_size_no_assignment_full_data(tmp_path):
    """The idiomatic no-assignment form `df.groupby('region').size()`.

    This returns an unnamed Series; the executor must normalise it to rows like
    [{region, count}] with TRUE full-data counts, not raw data rows.
    """
    path, expected, total = _write_skewed_csv(tmp_path)
    code = "df.groupby('region').size()"
    out = execute_code(code, path)
    assert out["traceback"] is None, out["traceback"]
    table = out["result_table"]
    assert "count" in table["columns"]
    assert "region" in table["columns"]
    counts = {r["region"]: r["count"] for r in table["rows"]}
    assert counts == expected
    assert sum(counts.values()) == total
    # Not masquerading raw rows: row_count is the number of GROUPS, not 5000+.
    assert table["row_count"] == len(expected)


def test_explicit_result_preferred_over_trailing_expression(tmp_path):
    path, expected, total = _write_skewed_csv(tmp_path)
    code = "result = len(df)\ndf.head()"
    out = execute_code(code, path)
    assert out["traceback"] is None, out["traceback"]
    assert out["result_table"]["rows"][0]["value"] == total


def test_no_result_value_returns_clean_error_not_raw_df(tmp_path):
    """No `result`, no trailing expression -> clean error, NEVER raw rows."""
    path, expected, total = _write_skewed_csv(tmp_path)
    # An assignment statement is the final node, so there is no trailing
    # expression and no `result` binding.
    code = "x = df.groupby('region').size()"
    out = execute_code(code, path)
    assert out["result_table"] is None
    assert out["traceback"] is not None
    # It must NOT have fabricated a table of raw rows.
    assert "no result value" in out["traceback"]
