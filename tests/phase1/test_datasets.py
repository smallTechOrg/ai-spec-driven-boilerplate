"""Phase-1 backend-datasets slice tests.

Covers the dataset store, the local profiler (privacy boundary), the upload API,
and the graceful unknown-dataset ask path. These do NOT require a real LLM call —
the unknown-dataset ask fails before any model is reached. The upload→ask LLM
end-to-end test and the build_prompt boundary test belong to backend-agent.
"""

import json

import pandas as pd
import pytest

from db.models import DatasetRow
from db import session as session_module
from datasets.store import save_dataset, dataset_path, get_dataset, DatasetError
from datasets.profiler import build_profile


# --------------------------------------------------------------------------- #
# Upload + profile (HTTP) and the storage privacy split
# --------------------------------------------------------------------------- #
def test_upload_and_profile(api_client, sales_csv_bytes, sales_df):
    resp = api_client.post(
        "/datasets",
        files={"file": ("sales.csv", sales_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    # dataset_id + correct row_count + schema returned.
    assert data["dataset_id"]
    assert data["filename"] == "sales.csv"
    assert data["row_count"] == len(sales_df)

    schema_names = {c["name"] for c in data["schema"]}
    assert {"region", "revenue", "units"} <= schema_names

    by_name = {c["name"]: c for c in data["schema"]}
    assert by_name["region"]["friendly_dtype"] == "text"
    assert by_name["revenue"]["friendly_dtype"] == "decimal"
    assert by_name["units"]["friendly_dtype"] == "integer"

    # The raw CSV exists on local disk at data/datasets/{id}.csv.
    raw_path = dataset_path(data["dataset_id"])
    assert raw_path.exists()
    assert raw_path.read_bytes() == sales_csv_bytes

    # The DB row holds metadata + schema ONLY — NO raw rows.
    from sqlalchemy.orm import Session

    with Session(session_module._engine) as s:
        row = s.get(DatasetRow, data["dataset_id"])
        assert row is not None
        assert row.row_count == len(sales_df)
        # Schema JSON contains only column metadata keys, never row values.
        stored = json.loads(row.schema_json)
        assert all(set(c.keys()) == {"name", "dtype", "friendly_dtype"} for c in stored)
        # A full data-row string must not be embedded anywhere in the persisted row.
        full_row = ",".join(str(v) for v in sales_df.iloc[0].tolist())
        serialized = f"{row.filename}|{row.schema_json}|{row.row_count}"
        assert full_row not in serialized
        # The model has no attribute that could hold raw rows.
        assert not hasattr(row, "raw_rows")
        assert not hasattr(row, "data")


def test_profiler_no_raw_rows(sales_csv_bytes, sales_df):
    row = save_dataset(sales_csv_bytes, "sales.csv")
    profile = build_profile(row.id)

    # Derived shape is present and correct.
    assert profile["row_count"] == len(sales_df)
    assert {c["name"] for c in profile["columns"]} >= {"region", "revenue", "units"}

    # Numeric stats for revenue match the local pandas computation.
    rstats = profile["stats"]["revenue"]
    assert rstats["kind"] == "numeric"
    assert rstats["mean"] == pytest.approx(float(sales_df["revenue"].mean()), rel=1e-6)
    assert rstats["min"] == pytest.approx(float(sales_df["revenue"].min()), rel=1e-6)
    assert rstats["max"] == pytest.approx(float(sales_df["revenue"].max()), rel=1e-6)

    # Categorical stats for region: distinct count + capped top values.
    cstats = profile["stats"]["region"]
    assert cstats["kind"] == "categorical"
    assert cstats["distinct_count"] == sales_df["region"].nunique()

    # Examples are capped at <=5 per column.
    for col, ex in profile["examples"].items():
        assert len(ex) <= 5

    # The privacy assertion: a full serialized data row must NOT appear verbatim
    # anywhere in the derived profile.
    serialized = json.dumps(profile, default=str)
    for i in range(len(sales_df)):
        full_row = ",".join(str(v) for v in sales_df.iloc[i].tolist())
        assert full_row not in serialized

    # The full revenue column (every value concatenated) must not leak either.
    full_revenue_col = ",".join(str(v) for v in sales_df["revenue"].tolist())
    assert full_revenue_col not in serialized


# --------------------------------------------------------------------------- #
# Rejection paths — graceful 400 with human copy
# --------------------------------------------------------------------------- #
def test_upload_rejects_non_csv(api_client):
    resp = api_client.post(
        "/datasets",
        files={"file": ("notes.txt", b"hello world this is not csv", "text/plain")},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"]
    assert "csv" in detail["message"].lower()


def test_upload_rejects_unparseable_csv(api_client):
    # .csv extension but binary garbage pandas cannot parse.
    garbage = bytes([0x00, 0xFF, 0xFE, 0x00, 0x01]) * 50
    resp = api_client.post(
        "/datasets",
        files={"file": ("broken.csv", garbage, "text/csv")},
    )
    assert resp.status_code == 400
    msg = resp.json()["detail"]["message"]
    assert isinstance(msg, str) and msg
    # Never a raw stack trace leaked to the client.
    assert "Traceback" not in msg


def test_upload_rejects_oversize(api_client, monkeypatch):
    import config.settings as settings_module

    # Force a tiny cap so a small file trips the limit deterministically.
    settings_module._settings = None
    monkeypatch.setenv("AGENT_MAX_UPLOAD_MB", "0")
    # max_upload_mb=0 -> any non-empty payload exceeds 0 bytes.
    payload = b"region,revenue\nWest,100\n"
    resp = api_client.post(
        "/datasets",
        files={"file": ("big.csv", payload, "text/csv")},
    )
    assert resp.status_code == 400
    assert "limit" in resp.json()["detail"]["message"].lower()


def test_upload_rejects_empty(api_client):
    resp = api_client.post(
        "/datasets",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["message"]


# --------------------------------------------------------------------------- #
# Ask route — unknown dataset returns a graceful failed response (no LLM call)
# --------------------------------------------------------------------------- #
def test_ask_unknown_dataset_graceful(api_client):
    resp = api_client.post(
        "/datasets/does-not-exist/ask",
        json={"question": "Which region has the highest total revenue?"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert data["dataset_id"] == "does-not-exist"
    assert data["answer"] is None
    assert data["error"] and isinstance(data["error"], str)
    assert data["run_id"] is None


def test_ask_empty_question_rejected(api_client):
    resp = api_client.post(
        "/datasets/some-id/ask",
        json={"question": "   "},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["message"]


# --------------------------------------------------------------------------- #
# Store-level unit checks
# --------------------------------------------------------------------------- #
def test_save_dataset_persists_metadata_only(sales_csv_bytes):
    row = save_dataset(sales_csv_bytes, "sales.csv")
    assert dataset_path(row.id).exists()
    from sqlalchemy.orm import Session

    with Session(session_module._engine) as s:
        fetched = get_dataset(s, row.id)
        assert fetched is not None
        assert fetched.filename == "sales.csv"


def test_save_dataset_rejects_non_csv_extension(sales_csv_bytes):
    with pytest.raises(DatasetError):
        save_dataset(sales_csv_bytes, "data.json")
