"""Ingestion + profiling — no LLM key required (all local DuckDB/pandas)."""
import io

import pandas as pd
import pytest

from data.ingest import (
    FileTooLargeError,
    IngestError,
    ingest_file,
)


def _csv_bytes() -> bytes:
    return (
        "region,amount,note\n"
        "West,100.0,a\n"
        "East,200.0,\n"          # null in note
        "West,300.5,c\n"
        "North,,d\n"             # null in amount
    ).encode("utf-8")


def test_ingest_csv_returns_single_dataset_with_profile(tmp_path):
    datasets = ingest_file(
        filename="sales.csv", content=_csv_bytes(), storage_dir=tmp_path
    )
    assert len(datasets) == 1
    d = datasets[0]
    assert d.source_kind == "csv"
    assert d.sheet_name is None
    assert d.name == "sales.csv"
    assert d.row_count == 4
    assert d.profile["row_count"] == 4

    cols = {c["name"]: c for c in d.profile["columns"]}
    assert set(cols) == {"region", "amount", "note"}
    # null counts computed from the full data
    assert cols["note"]["null_count"] == 1
    assert cols["amount"]["null_count"] == 1
    # numeric stats present for amount
    assert cols["amount"]["min"] == 100.0
    assert cols["amount"]["max"] == 300.5
    assert cols["amount"]["mean"] == pytest.approx(200.166666, rel=1e-3)


def test_ingest_excel_multi_sheet_returns_one_dataset_per_sheet(tmp_path):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}).to_excel(
            writer, sheet_name="Sheet1", index=False
        )
        pd.DataFrame({"c": [10.0, 20.0]}).to_excel(
            writer, sheet_name="Totals", index=False
        )
    content = buf.getvalue()

    datasets = ingest_file(
        filename="book.xlsx", content=content, storage_dir=tmp_path
    )
    assert len(datasets) == 2
    names = sorted(d.sheet_name for d in datasets)
    assert names == ["Sheet1", "Totals"]
    by_sheet = {d.sheet_name: d for d in datasets}
    assert by_sheet["Sheet1"].row_count == 3
    assert by_sheet["Totals"].row_count == 2
    assert all(d.source_kind == "excel" for d in datasets)
    assert "book.xlsx — Sheet1" == by_sheet["Sheet1"].name


def test_empty_file_is_rejected(tmp_path):
    with pytest.raises(IngestError):
        ingest_file(filename="empty.csv", content=b"", storage_dir=tmp_path)


def test_unsupported_extension_is_rejected(tmp_path):
    with pytest.raises(IngestError):
        ingest_file(
            filename="data.json", content=b'{"a":1}', storage_dir=tmp_path
        )


def test_header_only_csv_is_rejected(tmp_path):
    with pytest.raises(IngestError):
        ingest_file(
            filename="headers.csv", content=b"a,b,c\n", storage_dir=tmp_path
        )


def test_oversize_file_is_rejected(tmp_path):
    with pytest.raises(FileTooLargeError):
        ingest_file(
            filename="big.csv",
            content=b"x" * 50,
            storage_dir=tmp_path,
            max_bytes=10,
        )


def test_sample_csv_profiles_correctly(tmp_path):
    from pathlib import Path

    sample = Path(__file__).resolve().parents[2] / "samples" / "sample_sales.csv"
    datasets = ingest_file(
        filename="sample_sales.csv",
        content=sample.read_bytes(),
        storage_dir=tmp_path,
    )
    d = datasets[0]
    assert d.row_count == 480
    cols = {c["name"] for c in d.profile["columns"]}
    assert {"region", "amount", "quantity", "customer_segment"} <= cols
