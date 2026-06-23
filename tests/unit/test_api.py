"""API contract tests — no LLM key required (graph not invoked)."""
import io

from sqlalchemy.orm import Session

from db.models import Dataset


def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_upload_dataset(api_client):
    csv = b"region,revenue\nWest,100\nEast,50\n"
    r = api_client.post(
        "/datasets",
        files={"file": ("sales.csv", io.BytesIO(csv), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "sales.csv"
    assert data["row_count"] == 2
    assert data["table_name"].startswith("ds_")
    names = {c["name"] for c in data["columns"]}
    assert names == {"region", "revenue"}


def test_upload_empty_file_rejected(api_client):
    r = api_client.post(
        "/datasets",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "EMPTY_FILE"


def test_upload_header_only_rejected(api_client):
    r = api_client.post(
        "/datasets",
        files={"file": ("h.csv", io.BytesIO(b"a,b,c\n"), "text/csv")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] in ("EMPTY_FILE", "BAD_CSV")


def test_list_datasets(api_client):
    api_client.post(
        "/datasets",
        files={"file": ("a.csv", io.BytesIO(b"x\n1\n2\n"), "text/csv")},
    )
    r = api_client.get("/datasets")
    assert r.status_code == 200
    assert len(r.json()["data"]) == 1


def test_get_dataset_not_found(api_client):
    r = api_client.get("/datasets/nope")
    assert r.status_code == 404


def test_query_unknown_dataset(api_client):
    r = api_client.post("/queries", json={"dataset_id": "nope", "question": "x?"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_query_empty_question_rejected(api_client, _isolated_db):
    with Session(_isolated_db) as s:
        ds = Dataset(name="t", table_name="ds_t", row_count=0)
        s.add(ds)
        s.commit()
        ds_id = ds.id
    r = api_client.post("/queries", json={"dataset_id": ds_id, "question": "  "})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "BAD_REQUEST"


def test_audit_empty_list(api_client):
    r = api_client.get("/audit")
    assert r.status_code == 200
    assert r.json()["data"] == []


def test_audit_after_upload(api_client):
    api_client.post(
        "/datasets",
        files={"file": ("a.csv", io.BytesIO(b"x\n1\n"), "text/csv")},
    )
    r = api_client.get("/audit")
    entries = r.json()["data"]
    assert len(entries) == 1
    assert entries[0]["operation"] == "ingest"
    assert entries[0]["success"] is True


def test_queries_empty_list(api_client):
    r = api_client.get("/queries")
    assert r.status_code == 200
    assert r.json()["data"] == []
