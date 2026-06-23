"""CSV ingest tests — no LLM key required."""
import json

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.models import AuditLogEntry, Dataset
from ingest.csv_loader import (
    BadCsvError,
    EmptyFileError,
    ingest_csv,
    table_name_for,
)

CSV = b"region,revenue,units\nWest,1000.5,10\nEast,500,5\nWest,250.25,3\n"


def test_table_name_safe():
    assert table_name_for("3f2a-bbbb-cccc") == "ds_3f2a_bbbb_cccc"


def test_ingest_creates_table_and_caches(_isolated_db):
    summary = ingest_csv(CSV, "sales.csv")

    assert summary["name"] == "sales.csv"
    assert summary["row_count"] == 3
    assert summary["table_name"].startswith("ds_")

    cols = {c["name"]: c["type"] for c in summary["columns"]}
    assert cols["region"] == "TEXT"
    assert cols["revenue"] == "REAL"
    assert cols["units"] == "INTEGER"

    # ds_ table created and populated
    with Session(_isolated_db) as s:
        cnt = s.execute(
            text(f'SELECT COUNT(*) FROM "{summary["table_name"]}"')
        ).scalar()
        assert cnt == 3

        ds = s.get(Dataset, summary["id"])
        assert ds.schema_text and "region" in ds.schema_text
        assert ds.sample_text and "West" in ds.sample_text
        assert json.loads(ds.columns_json)[0]["name"] == "region"


def test_ingest_writes_audit(_isolated_db):
    summary = ingest_csv(CSV, "sales.csv")
    with Session(_isolated_db) as s:
        audits = s.query(AuditLogEntry).filter_by(operation="ingest").all()
        assert len(audits) == 1
        a = audits[0]
        assert a.success is True
        assert a.dataset_id == summary["id"]
        assert a.duration_ms >= 0
        assert a.row_count == 3


def test_sample_capped_at_20(_isolated_db):
    rows = b"n\n" + b"".join(f"{i}\n".encode() for i in range(50))
    summary = ingest_csv(rows, "big.csv")
    with Session(_isolated_db) as s:
        ds = s.get(Dataset, summary["id"])
    # sample_text has header + at most 20 data lines
    assert len(ds.sample_text.splitlines()) <= 21
    assert summary["row_count"] == 50


def test_empty_file_rejected(_isolated_db):
    with pytest.raises(EmptyFileError):
        ingest_csv(b"", "empty.csv")


def test_header_only_is_empty(_isolated_db):
    with pytest.raises(EmptyFileError):
        ingest_csv(b"a,b,c\n", "headeronly.csv")


def test_empty_cells_become_null(_isolated_db):
    csv = b"a,b\n1,\n2,x\n"
    summary = ingest_csv(csv, "nulls.csv")
    with Session(_isolated_db) as s:
        vals = s.execute(
            text(f'SELECT b FROM "{summary["table_name"]}" ORDER BY a')
        ).fetchall()
    assert vals[0][0] is None
    assert vals[1][0] == "x"
