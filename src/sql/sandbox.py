"""Read-only SQL sandbox.

Generated SQL is untrusted model output. Before any execution it must pass
validation: a single read-only ``SELECT`` (or ``WITH ... SELECT``) referencing
only the allowed dataset table(s). Execution is read-only with a row cap so a
runaway query cannot exhaust memory.
"""
import re
import time
from collections.abc import Sequence

DEFAULT_ROW_CAP = 5000

# Tokens that must never appear in generated SQL (case-insensitive, word-boundary).
_BANNED_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REPLACE", "TRUNCATE",
    "REINDEX", "ANALYZE", "GRANT", "REVOKE",
)


class SandboxViolation(Exception):
    """Raised when generated SQL fails validation."""


def _strip_comments(sql: str) -> str:
    """Remove -- line comments and /* */ block comments (anti-bypass)."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def validate_sql(sql: str, allowed_tables: Sequence[str]) -> str:
    """Validate that ``sql`` is a single read-only SELECT over allowed tables.

    Returns the cleaned single-statement SQL (trailing ``;`` stripped).
    Raises :class:`SandboxViolation` on any violation.
    """
    if not sql or not sql.strip():
        raise SandboxViolation("Empty SQL")

    cleaned = _strip_comments(sql).strip()

    # Reject multiple statements: only one trailing ';' is tolerated.
    stripped = cleaned.rstrip().rstrip(";").rstrip()
    if ";" in stripped:
        raise SandboxViolation("Multiple SQL statements are not allowed")

    upper = stripped.upper()

    # Must begin with SELECT or WITH (CTE that yields a SELECT).
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise SandboxViolation("Only a single read-only SELECT is allowed")

    # Banned keywords anywhere (word-boundary match).
    for kw in _BANNED_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            raise SandboxViolation(f"Disallowed SQL keyword: {kw}")

    # Table allow-list: every ds_-prefixed identifier referenced must be allowed,
    # and no ORM/metadata table may be referenced.
    allowed = {t.lower() for t in allowed_tables}
    referenced = _referenced_tables(stripped)
    for tbl in referenced:
        if tbl.lower() not in allowed:
            raise SandboxViolation(
                f"Query references disallowed table: {tbl}"
            )

    return stripped


def _referenced_tables(sql: str) -> set[str]:
    """Extract identifiers following FROM / JOIN clauses."""
    tables: set[str] = set()
    for m in re.finditer(
        r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", sql, flags=re.IGNORECASE
    ):
        tables.add(m.group(1))
    return tables


def execute_select(
    connection,
    sql: str,
    allowed_tables: Sequence[str],
    *,
    row_cap: int = DEFAULT_ROW_CAP,
) -> dict:
    """Validate then execute a read-only SELECT on a raw sqlite3 ``connection``.

    Returns a dict: ``columns``, ``rows`` (list[list]), ``row_count``,
    ``duration_ms``, ``sql`` (the validated SQL string).
    Raises :class:`SandboxViolation` on validation failure; the caller catches
    execution errors.
    """
    validated = validate_sql(sql, allowed_tables)

    # Enforce read-only at the connection level as a second guard.
    connection.execute("PRAGMA query_only = ON")

    start = time.perf_counter()
    cursor = connection.execute(validated)
    columns = [d[0] for d in cursor.description] if cursor.description else []
    raw_rows = cursor.fetchmany(row_cap)
    rows = [list(r) for r in raw_rows]
    duration_ms = int((time.perf_counter() - start) * 1000)

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "duration_ms": duration_ms,
        "sql": validated,
    }
