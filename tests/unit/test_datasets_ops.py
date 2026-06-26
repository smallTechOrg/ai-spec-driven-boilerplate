"""Offline unit suite for the slice-4b dataset-operations routes.

Stub provider + isolated SQLite (conftest `_isolated_db`), zero network. Covers
the deterministic contract WITHOUT asserting any LLM-generated CONTENT:

- PATCH /datasets/{id}/context: > 4000 chars -> 400 `context_too_long`; stores a
  valid context; 404 on a missing id.
- POST /datasets/{id}/clean: a generated expression that RAISES at exec time -> 422
  `clean_error` (we monkeypatch the LLM to return a broken expression); a valid
  generated expression -> 200 with before/after counts and the stored file
  UNCHANGED; 404 on a missing id.
- POST /datasets/{id}/clean/apply: a valid `code` body -> 200 and the row counts
  update; a broken `code` -> 422.
- POST /datasets/{id}/describe: sets `auto_notes_status="pending"`; 404 missing.

The real-Gemini CONTENT gate lives in tests/integration/test_clean_real.py and
tests/integration/test_describe_real.py.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _force_stub_provider(monkeypatch):
    """Pin the offline stub provider regardless of any key present in `.env`."""
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "stub")
    import config.settings as m
    m._settings = None


@pytest.fixture
def ops_client(_isolated_db):
    """A TestClient over a minimal app mounting ONLY the datasets_ops router."""
    from api.datasets_ops import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def make_dataset(tmp_path):
    """Create a dataset row + on-disk CSV/Parquet; return its id."""
    from db.models import DatasetRow
    from db.session import create_db_session

    uploads = tmp_path / "uploads"
    uploads.mkdir(exist_ok=True)

    def _make(df: pd.DataFrame, filename: str = "data.csv") -> str:
        with create_db_session() as session:
            row = DatasetRow(
                filename=filename,
                file_path="",
                row_count=len(df),
                col_count=len(df.columns),
                columns_json=[{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns],
                content_hash=f"hash-{filename}",
                format="csv",
                origin="uploaded",
            )
            session.add(row)
            session.flush()
            dataset_id = row.id
            csv_path = uploads / f"{dataset_id}.csv"
            parquet_path = uploads / f"{dataset_id}.parquet"
            df.to_csv(csv_path, index=False)
            df.to_parquet(parquet_path, index=False)
            row.file_path = str(csv_path)
            row.parquet_path = str(parquet_path)
        return dataset_id

    return _make


def _set_clean_code(monkeypatch, code: str) -> None:
    """Make every LLMClient.call_model return `code` (a pandas expression)."""
    monkeypatch.setattr(
        "llm.client.LLMClient.call_model",
        lambda self, prompt, *, system=None: code,
    )


# --------------------------------------------------------------------------- #
# PATCH /datasets/{id}/context
# --------------------------------------------------------------------------- #


def test_patch_context_stores_value(ops_client, make_dataset):
    ds = make_dataset(pd.DataFrame({"a": [1, 2, 3]}))
    r = ops_client.patch(f"/datasets/{ds}/context", json={"context": "Sales for FY24."})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["context"] == "Sales for FY24."


def test_patch_context_too_long_400(ops_client, make_dataset):
    ds = make_dataset(pd.DataFrame({"a": [1, 2, 3]}))
    r = ops_client.patch(f"/datasets/{ds}/context", json={"context": "x" * 4001})
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["code"] == "context_too_long"


def test_patch_context_at_limit_ok(ops_client, make_dataset):
    ds = make_dataset(pd.DataFrame({"a": [1, 2, 3]}))
    r = ops_client.patch(f"/datasets/{ds}/context", json={"context": "x" * 4000})
    assert r.status_code == 200, r.text


def test_patch_context_missing_404(ops_client):
    r = ops_client.patch("/datasets/nope/context", json={"context": "hi"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "not_found"


# --------------------------------------------------------------------------- #
# POST /datasets/{id}/clean  (preview)
# --------------------------------------------------------------------------- #


def test_clean_preview_valid_code_does_not_mutate(ops_client, make_dataset, monkeypatch):
    df = pd.DataFrame({"a": [1, 2, None, 4], "b": [10, 20, 30, 40]})
    ds = make_dataset(df)  # 4 rows
    _set_clean_code(monkeypatch, "df.dropna()")

    r = ops_client.post(f"/datasets/{ds}/clean", json={"instruction": "drop nulls"})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["code"] == "df.dropna()"
    assert data["before"]["rows"] == 4
    assert data["after"]["rows"] == 3  # one null row dropped
    assert isinstance(data["preview_before"], list)
    assert isinstance(data["preview_after"], list)

    # The stored dataset is UNCHANGED (preview runs on a copy).
    from db.models import DatasetRow
    from db.session import create_db_session
    with create_db_session() as session:
        row = session.get(DatasetRow, ds)
        assert row.row_count == 4


def test_clean_preview_exec_error_422(ops_client, make_dataset, monkeypatch):
    ds = make_dataset(pd.DataFrame({"a": [1, 2, 3]}))
    # A column that does not exist -> KeyError at eval time -> recoverable error.
    _set_clean_code(monkeypatch, "df[df['nonexistent'] > 0]")

    r = ops_client.post(f"/datasets/{ds}/clean", json={"instruction": "filter"})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "clean_error"


def test_clean_preview_non_dataframe_result_422(ops_client, make_dataset, monkeypatch):
    ds = make_dataset(pd.DataFrame({"a": [1, 2, 3]}))
    # A scalar result is not a DataFrame -> 422.
    _set_clean_code(monkeypatch, "df['a'].sum()")

    r = ops_client.post(f"/datasets/{ds}/clean", json={"instruction": "sum"})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "clean_error"


def test_clean_preview_missing_dataset_404(ops_client, monkeypatch):
    _set_clean_code(monkeypatch, "df.dropna()")
    r = ops_client.post("/datasets/nope/clean", json={"instruction": "drop"})
    assert r.status_code == 404


def test_clean_preview_empty_instruction_400(ops_client, make_dataset):
    ds = make_dataset(pd.DataFrame({"a": [1, 2, 3]}))
    r = ops_client.post(f"/datasets/{ds}/clean", json={"instruction": "   "})
    assert r.status_code == 400


# --------------------------------------------------------------------------- #
# POST /datasets/{id}/clean/apply
# --------------------------------------------------------------------------- #


def test_clean_apply_updates_counts_and_file(ops_client, make_dataset):
    df = pd.DataFrame({"a": [1, 2, None, 4], "b": [10, 20, 30, 40]})
    ds = make_dataset(df)  # 4 rows

    r = ops_client.post(f"/datasets/{ds}/clean/apply", json={"code": "df.dropna()"})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["row_count"] == 3

    # Row metadata updated.
    from db.models import DatasetRow
    from db.session import create_db_session
    with create_db_session() as session:
        row = session.get(DatasetRow, ds)
        assert row.row_count == 3
        # On-disk CSV reflects the apply.
        on_disk = pd.read_csv(row.file_path)
        assert len(on_disk) == 3


def test_clean_apply_exec_error_422(ops_client, make_dataset):
    ds = make_dataset(pd.DataFrame({"a": [1, 2, 3]}))
    r = ops_client.post(
        f"/datasets/{ds}/clean/apply", json={"code": "df['missing'].dropna()"}
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "clean_error"


def test_clean_apply_missing_dataset_404(ops_client):
    r = ops_client.post("/datasets/nope/clean/apply", json={"code": "df.dropna()"})
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# POST /datasets/{id}/describe
# --------------------------------------------------------------------------- #


def test_describe_sets_pending(ops_client, make_dataset, monkeypatch):
    # Don't actually run the async notes job in this offline test — assert it set
    # pending and returned immediately. We stub the trigger to a no-op.
    monkeypatch.setattr("api.datasets_ops.trigger_describe_async", lambda _id: None)

    ds = make_dataset(pd.DataFrame({"a": [1, 2, 3]}))
    r = ops_client.post(f"/datasets/{ds}/describe")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["auto_notes_status"] == "pending"

    from db.models import DatasetRow
    from db.session import create_db_session
    with create_db_session() as session:
        row = session.get(DatasetRow, ds)
        assert row.auto_notes_status == "pending"


def test_describe_missing_dataset_404(ops_client, monkeypatch):
    monkeypatch.setattr("api.datasets_ops.trigger_describe_async", lambda _id: None)
    r = ops_client.post("/datasets/nope/describe")
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# C31 compress helper (offline -> [] by design, never raises)
# --------------------------------------------------------------------------- #


def test_extract_facts_from_text_empty_offline():
    from graph.compress import extract_facts_from_text

    # Stub provider has no <node:compress> branch -> non-JSON -> [] by design.
    assert extract_facts_from_text("Revenue is in GBP.") == []
    assert extract_facts_from_text("") == []


def test_extract_facts_writes_empty_offline(make_dataset):
    from graph.compress import extract_facts

    ds = make_dataset(pd.DataFrame({"a": [1, 2, 3]}))
    # No context set -> nothing to compress -> [].
    assert extract_facts(ds) == []
