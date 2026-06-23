"""CSV ingest: parse a CSV into a real, queryable ``ds_<id>`` SQLite table.

Infers a SQLite affinity per column (INTEGER / REAL / TEXT; empty -> NULL),
creates the dynamic table, bulk-inserts rows with parameterised SQL, and caches
``columns_json`` / ``schema_text`` / ``sample_text`` / ``row_count`` on the
``datasets`` row. Writes an ``audit_log`` op=``ingest`` entry (success or
failure).
"""
import csv
import io
import json
import re
import time

from db.models import AuditLogEntry, Dataset
from db.session import create_db_session, _get_engine

SAMPLE_ROWS = 20


class BadCsvError(Exception):
    """Malformed CSV / missing header."""


class EmptyFileError(Exception):
    """Empty upload / no data rows."""


def table_name_for(dataset_id: str) -> str:
    """ds_ + UUID with hyphens replaced by underscores (valid SQL identifier)."""
    return "ds_" + dataset_id.replace("-", "_")


def _sanitize_column(name: str, index: int) -> str:
    """Make a CSV header a safe SQL identifier."""
    cleaned = re.sub(r"[^0-9A-Za-z_]", "_", (name or "").strip())
    cleaned = cleaned.strip("_")
    if not cleaned:
        cleaned = f"col_{index}"
    if cleaned[0].isdigit():
        cleaned = f"c_{cleaned}"
    return cleaned


def _is_int(v: str) -> bool:
    try:
        int(v)
        return True
    except (ValueError, TypeError):
        return False


def _is_float(v: str) -> bool:
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def _infer_affinity(values: list[str]) -> str:
    """INTEGER if all non-empty values are ints; REAL if all numeric; else TEXT."""
    non_empty = [v for v in values if v is not None and v != ""]
    if not non_empty:
        return "TEXT"
    if all(_is_int(v) for v in non_empty):
        return "INTEGER"
    if all(_is_float(v) for v in non_empty):
        return "REAL"
    return "TEXT"


def _coerce(value: str, affinity: str):
    if value is None or value == "":
        return None
    if affinity == "INTEGER":
        return int(value)
    if affinity == "REAL":
        return float(value)
    return value


def _quote_ident(identifier: str) -> str:
    """Safely quote a SQL identifier (double-quote, escape internal quotes)."""
    return '"' + identifier.replace('"', '""') + '"'


def _parse_csv(raw: bytes) -> tuple[list[str], list[list[str]]]:
    if not raw or not raw.strip():
        raise EmptyFileError("Uploaded file is empty")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.reader(io.StringIO(text))
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise BadCsvError(f"Could not parse CSV: {exc}") from exc
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if not rows:
        raise EmptyFileError("CSV has no rows")
    header = rows[0]
    if not header or all(not (h or "").strip() for h in header):
        raise BadCsvError("CSV is missing a header row")
    data_rows = rows[1:]
    if not data_rows:
        raise EmptyFileError("CSV has a header but no data rows")
    return header, data_rows


def _build_schema_text(table_name: str, columns: list[dict]) -> str:
    cols = ", ".join(f"{c['name']} {c['type']}" for c in columns)
    return f"TABLE {table_name} ({cols})"


def _build_sample_text(columns: list[dict], sample: list[list]) -> str:
    header = " | ".join(c["name"] for c in columns)
    lines = [header]
    for row in sample:
        lines.append(" | ".join("" if v is None else str(v) for v in row))
    return "\n".join(lines)


def ingest_csv(raw: bytes, name: str) -> dict:
    """Ingest CSV bytes. Returns the dataset summary dict on success.

    Raises BadCsvError / EmptyFileError for client errors. Any unexpected error
    is re-raised after a failed audit entry is written.
    """
    start = time.perf_counter()

    header, data_rows = _parse_csv(raw)

    # Build column metadata + inferred types.
    n_cols = len(header)
    col_names = [_sanitize_column(h, i) for i, h in enumerate(header)]
    # Deduplicate sanitized names.
    seen: dict[str, int] = {}
    for i, cn in enumerate(col_names):
        if cn in seen:
            seen[cn] += 1
            col_names[i] = f"{cn}_{seen[cn]}"
        else:
            seen[cn] = 0

    # Normalise ragged rows to n_cols.
    norm_rows = [
        (r + [""] * n_cols)[:n_cols] for r in data_rows
    ]

    columns_meta = []
    for ci in range(n_cols):
        col_values = [r[ci] for r in norm_rows]
        affinity = _infer_affinity(col_values)
        columns_meta.append({"name": col_names[ci], "type": affinity})

    # Create dataset row first to obtain an id.
    with create_db_session() as session:
        ds = Dataset(name=name, table_name="", row_count=0)
        session.add(ds)
        session.flush()
        dataset_id = ds.id

    tbl = table_name_for(dataset_id)

    try:
        _create_and_load(tbl, columns_meta, norm_rows)
    except Exception as exc:  # noqa: BLE001 - record audit then re-raise
        duration_ms = int((time.perf_counter() - start) * 1000)
        with create_db_session() as session:
            session.add(
                AuditLogEntry(
                    operation="ingest",
                    dataset_id=dataset_id,
                    sql_text=f"LOAD {tbl}",
                    row_count=0,
                    columns_json=json.dumps([c["name"] for c in columns_meta]),
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(exc),
                )
            )
        raise

    row_count = len(norm_rows)
    sample = [
        [_coerce(r[ci], columns_meta[ci]["type"]) for ci in range(n_cols)]
        for r in norm_rows[:SAMPLE_ROWS]
    ]
    schema_text = _build_schema_text(tbl, columns_meta)
    sample_text = _build_sample_text(columns_meta, sample)
    columns_json = json.dumps(columns_meta)

    with create_db_session() as session:
        ds = session.get(Dataset, dataset_id)
        ds.table_name = tbl
        ds.row_count = row_count
        ds.columns_json = columns_json
        ds.schema_text = schema_text
        ds.sample_text = sample_text
        created_at = ds.created_at

    duration_ms = int((time.perf_counter() - start) * 1000)
    with create_db_session() as session:
        session.add(
            AuditLogEntry(
                operation="ingest",
                dataset_id=dataset_id,
                sql_text=f"CREATE TABLE {tbl} + load {row_count} rows",
                row_count=row_count,
                columns_json=json.dumps([c["name"] for c in columns_meta]),
                duration_ms=duration_ms,
                success=True,
            )
        )

    return {
        "id": dataset_id,
        "name": name,
        "table_name": tbl,
        "row_count": row_count,
        "columns": columns_meta,
        "created_at": created_at,
    }


def _create_and_load(tbl: str, columns_meta: list[dict], rows: list[list[str]]) -> None:
    """Create the dynamic ds_ table and bulk-insert rows via the raw sqlite conn."""
    quoted_tbl = _quote_ident(tbl)
    col_defs = ", ".join(
        f"{_quote_ident(c['name'])} {c['type']}" for c in columns_meta
    )
    placeholders = ", ".join("?" for _ in columns_meta)
    insert_sql = f"INSERT INTO {quoted_tbl} VALUES ({placeholders})"

    raw_conn = _get_engine().raw_connection()
    try:
        cur = raw_conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {quoted_tbl}")
        cur.execute(f"CREATE TABLE {quoted_tbl} ({col_defs})")
        coerced = [
            [_coerce(r[ci], columns_meta[ci]["type"]) for ci in range(len(columns_meta))]
            for r in rows
        ]
        if coerced:
            cur.executemany(insert_sql, coerced)
        raw_conn.commit()
    finally:
        raw_conn.close()
