"""Phase 2 integration: auto-profiling on upload (no LLM key required).

Uploads the real olist CSV through the API and asserts the per-column profile is
computed, shaped correctly, returned on the upload response, AND persisted to
DatasetRow.profile_json.
"""
import io
import json
from pathlib import Path

from sqlalchemy.orm import Session

from db.models import DatasetRow

OLIST = (
    Path(__file__).resolve().parent.parent.parent
    / "src" / "data" / "datasets"
    / "8bc76e9e-1151-437e-95eb-727b57b674ee"
    / "olist_orders_dataset.csv"
)


def _by_name(profile, name):
    return next((c for c in profile if c["name"] == name), None)


def test_upload_returns_and_persists_profile(api_client, _isolated_db):
    assert OLIST.exists(), f"sample CSV missing at {OLIST}"
    with OLIST.open("rb") as fh:
        data = fh.read()

    up = api_client.post(
        "/datasets",
        files={"file": (OLIST.name, io.BytesIO(data), "text/csv")},
    )
    assert up.status_code == 200, up.text
    body = up.json()["data"]
    dataset_id = body["dataset_id"]

    profile = body["profile"]
    assert isinstance(profile, list) and profile, "profile must be a non-empty list"

    # One entry per schema column, each with the contract fields.
    schema_names = {c["name"] for c in body["schema"]}
    profile_names = {c["name"] for c in profile}
    assert profile_names == schema_names
    for col in profile:
        for key in ("name", "dtype", "type_category", "missing", "distinct",
                    "min", "max", "examples"):
            assert key in col, f"{col['name']} missing {key}"
        assert isinstance(col["missing"], int)
        assert isinstance(col["distinct"], int)
        assert isinstance(col["examples"], list)

    # order_status is categorical: sensible distinct + missing, no numeric range.
    status = _by_name(profile, "order_status")
    assert status is not None
    assert status["type_category"] in ("categorical", "text")
    assert 1 <= status["distinct"] <= 20  # olist has a handful of statuses
    assert status["missing"] == 0
    assert status["min"] is None and status["max"] is None
    assert status["examples"]

    # A datetime column (the order timestamps) must carry a min/max range.
    ts = _by_name(profile, "order_purchase_timestamp")
    assert ts is not None
    assert ts["type_category"] == "datetime"
    assert ts["min"] is not None and ts["max"] is not None
    assert str(ts["min"]) <= str(ts["max"])

    # Persisted to the DB.
    with Session(_isolated_db) as s:
        ds = s.get(DatasetRow, dataset_id)
        assert ds is not None
        assert ds.profile_json, "profile_json must be persisted (non-null)"
        persisted = json.loads(ds.profile_json)
        assert {c["name"] for c in persisted} == schema_names


def test_small_upload_profile_numeric_and_categorical(api_client, _isolated_db):
    csv = b"city,pop\nA,10\nB,20\nA,\n"
    up = api_client.post(
        "/datasets",
        files={"file": ("cities.csv", io.BytesIO(csv), "text/csv")},
    )
    assert up.status_code == 200
    profile = up.json()["data"]["profile"]

    pop = _by_name(profile, "pop")
    assert pop["type_category"] == "numeric"
    assert pop["missing"] == 1
    assert pop["min"] == 10 and pop["max"] == 20

    city = _by_name(profile, "city")
    assert city["type_category"] == "categorical"
    assert city["distinct"] == 2
    assert city["missing"] == 0


def test_profile_failure_degrades_upload(api_client, monkeypatch):
    """If profiling raises, the upload still succeeds with profile null."""
    import api.datasets as datasets_mod

    def _boom(_path):
        raise RuntimeError("profiler exploded")

    monkeypatch.setattr(datasets_mod, "compute_profile", _boom)

    csv = b"a,b\n1,2\n3,4\n"
    up = api_client.post(
        "/datasets",
        files={"file": ("ok.csv", io.BytesIO(csv), "text/csv")},
    )
    assert up.status_code == 200, up.text
    body = up.json()["data"]
    # Upload succeeded; profile degraded to null. Schema/sample still present.
    assert body["profile"] is None
    assert body["schema"]
    assert body["sample"]
