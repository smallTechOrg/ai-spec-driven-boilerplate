"""Local DuckDB engine — read-only enforcement + correct aggregates. No LLM."""
import pytest

from data.duckdb_engine import DatasetRef, QueryError, duckdb_query


@pytest.fixture
def csv_ref(tmp_path):
    path = tmp_path / "sales.csv"
    path.write_text(
        "region,amount\nWest,100\nEast,200\nWest,300\nEast,50\n",
        encoding="utf-8",
    )
    return DatasetRef(
        dataset_id="ds1",
        source_path=str(path),
        source_kind="csv",
        duckdb_table="ds",
    )


def test_select_aggregate_returns_correct_totals(csv_ref):
    rows, cols = duckdb_query(
        "SELECT region, SUM(amount) AS total FROM ds GROUP BY region ORDER BY total DESC",
        csv_ref,
    )
    assert {c["name"] for c in cols} == {"region", "total"}
    totals = {r["region"]: r["total"] for r in rows}
    assert totals["West"] == 400
    assert totals["East"] == 250
    # ordered descending by total
    assert rows[0]["region"] == "West"


def test_non_select_is_rejected(csv_ref):
    with pytest.raises(QueryError):
        duckdb_query("DELETE FROM ds", csv_ref)


def test_ddl_is_rejected(csv_ref):
    with pytest.raises(QueryError):
        duckdb_query("DROP TABLE ds", csv_ref)


def test_multi_statement_injection_is_rejected(csv_ref):
    with pytest.raises(QueryError):
        duckdb_query("SELECT 1; DROP TABLE ds", csv_ref)


def test_select_with_forbidden_keyword_is_rejected(csv_ref):
    with pytest.raises(QueryError):
        duckdb_query("SELECT * FROM ds; INSERT INTO ds VALUES ('X', 1)", csv_ref)


def test_with_cte_select_is_allowed(csv_ref):
    rows, _ = duckdb_query(
        "WITH t AS (SELECT region, SUM(amount) s FROM ds GROUP BY region) "
        "SELECT MAX(s) AS top FROM t",
        csv_ref,
    )
    assert rows[0]["top"] == 400


def test_bad_sql_raises_query_error(csv_ref):
    with pytest.raises(QueryError):
        duckdb_query("SELECT nonexistent_col FROM ds", csv_ref)
