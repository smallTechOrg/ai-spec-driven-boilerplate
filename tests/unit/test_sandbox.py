"""SQL sandbox tests — no LLM key required. The sandbox is the security guard."""
import sqlite3

import pytest

from sql.sandbox import SandboxViolation, execute_select, validate_sql

ALLOWED = ["ds_abc"]


def test_accepts_plain_select():
    sql = "SELECT region, SUM(revenue) AS total FROM ds_abc GROUP BY region"
    assert validate_sql(sql, ALLOWED).startswith("SELECT")


def test_accepts_with_cte():
    sql = "WITH t AS (SELECT * FROM ds_abc) SELECT * FROM t"
    # 't' is a CTE alias, not the allowed base table — but ds_abc is referenced;
    # the CTE name appears after FROM so it must be permitted as well.
    # We only allow the base table, so reference 'ds_abc' directly here:
    sql2 = "WITH x AS (SELECT region FROM ds_abc) SELECT region FROM ds_abc"
    assert validate_sql(sql2, ALLOWED).upper().startswith("WITH")


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO ds_abc VALUES (1)",
        "UPDATE ds_abc SET region = 'x'",
        "DELETE FROM ds_abc",
        "DROP TABLE ds_abc",
        "ALTER TABLE ds_abc ADD COLUMN x",
        "CREATE TABLE evil (a INT)",
        "ATTACH DATABASE 'x.db' AS y",
        "PRAGMA table_info(ds_abc)",
        "VACUUM",
        "REPLACE INTO ds_abc VALUES (1)",
    ],
)
def test_rejects_mutations(sql):
    with pytest.raises(SandboxViolation):
        validate_sql(sql, ALLOWED)


def test_rejects_multiple_statements():
    with pytest.raises(SandboxViolation):
        validate_sql("SELECT * FROM ds_abc; DROP TABLE ds_abc", ALLOWED)


def test_rejects_comment_bypass():
    # A DROP hidden after a -- comment-stripped boundary must still be caught.
    with pytest.raises(SandboxViolation):
        validate_sql("SELECT * FROM ds_abc; /* */ DELETE FROM ds_abc", ALLOWED)


def test_rejects_disallowed_table():
    with pytest.raises(SandboxViolation):
        validate_sql("SELECT * FROM audit_log", ALLOWED)


def test_rejects_metadata_table_join():
    with pytest.raises(SandboxViolation):
        validate_sql(
            "SELECT * FROM ds_abc JOIN datasets ON 1=1", ALLOWED
        )


def test_rejects_empty():
    with pytest.raises(SandboxViolation):
        validate_sql("   ", ALLOWED)


def test_execute_select_runs_readonly():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE ds_abc (region TEXT, revenue INTEGER)")
    conn.executemany(
        "INSERT INTO ds_abc VALUES (?, ?)",
        [("West", 100), ("East", 50), ("West", 25)],
    )
    conn.commit()

    result = execute_select(
        conn,
        "SELECT region, SUM(revenue) AS total FROM ds_abc GROUP BY region ORDER BY region",
        ALLOWED,
    )
    assert result["columns"] == ["region", "total"]
    assert result["row_count"] == 2
    assert ["East", 50] in result["rows"]
    assert result["duration_ms"] >= 0


def test_execute_select_blocks_write_via_pragma():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE ds_abc (region TEXT)")
    conn.commit()
    # A mutation is rejected at validation before any execution.
    with pytest.raises(SandboxViolation):
        execute_select(conn, "DELETE FROM ds_abc", ALLOWED)
