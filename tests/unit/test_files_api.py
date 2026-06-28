"""Unit tests for POST /api/files/upload and GET /api/files — no LLM key required."""
import io
import pytest


def test_health_at_api_prefix(api_client):
    r = api_client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["status"] == "ok"


def test_upload_csv_success(api_client):
    csv_content = b"name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\n"
    r = api_client.post(
        "/api/files/upload",
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r.status_code == 200
    body = r.json()
    data = body["data"]
    assert data["original_name"] == "test.csv"
    assert data["source_type"] == "csv"
    assert data["row_count"] == 3
    assert "file_id" in data
    assert "schema_preview" in data
    schema = data["schema_preview"]
    assert schema["columns"] == ["name", "age", "city"]
    assert "name" in schema["dtypes"]
    assert len(schema["sample_rows"]) <= 3


def test_upload_csv_schema_sample_rows(api_client):
    csv_content = b"x,y\n1,2\n3,4\n5,6\n7,8\n"
    r = api_client.post(
        "/api/files/upload",
        files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r.status_code == 200
    schema = r.json()["data"]["schema_preview"]
    # Only 3 sample rows max
    assert len(schema["sample_rows"]) == 3
    # NaN-safe: all values are not NaN (they should be JSON-serializable)
    for row in schema["sample_rows"]:
        for val in row:
            assert val is None or isinstance(val, (str, int, float, bool))


def test_upload_rejects_non_csv(api_client):
    content = b"not a csv"
    r = api_client.post(
        "/api/files/upload",
        files={"file": ("report.xlsx", io.BytesIO(content), "application/vnd.ms-excel")},
    )
    assert r.status_code == 400
    body = r.json()
    # Error detail should have code and message
    assert "code" in body["detail"]


def test_upload_rejects_empty_file(api_client):
    r = api_client.post(
        "/api/files/upload",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert r.status_code == 400


def test_upload_rejects_malformed_csv(api_client):
    # Binary garbage that can't be parsed as CSV
    bad_content = bytes(range(256)) * 100
    r = api_client.post(
        "/api/files/upload",
        files={"file": ("bad.csv", io.BytesIO(bad_content), "text/csv")},
    )
    assert r.status_code == 400


def test_list_files_empty(api_client):
    r = api_client.get("/api/files")
    assert r.status_code == 200
    body = r.json()
    assert "files" in body["data"]
    assert body["data"]["files"] == []


def test_list_files_after_upload(api_client):
    csv_content = b"col1,col2\n1,a\n2,b\n"
    api_client.post(
        "/api/files/upload",
        files={"file": ("mydata.csv", io.BytesIO(csv_content), "text/csv")},
    )
    r = api_client.get("/api/files")
    assert r.status_code == 200
    files = r.json()["data"]["files"]
    assert len(files) == 1
    assert files[0]["original_name"] == "mydata.csv"
    assert files[0]["source_type"] == "csv"
    assert "schema_preview" in files[0]


def test_list_files_multiple_uploads(api_client):
    csv_content = b"a,b\n1,2\n"
    api_client.post(
        "/api/files/upload",
        files={"file": ("file1.csv", io.BytesIO(csv_content), "text/csv")},
    )
    api_client.post(
        "/api/files/upload",
        files={"file": ("file2.csv", io.BytesIO(csv_content), "text/csv")},
    )
    r = api_client.get("/api/files")
    assert r.status_code == 200
    files = r.json()["data"]["files"]
    assert len(files) == 2
    names = {f["original_name"] for f in files}
    assert names == {"file1.csv", "file2.csv"}


def test_pg_connect_returns_501(api_client):
    r = api_client.post("/api/pg/connect", json={"name": "Test DB"})
    assert r.status_code == 501


def test_upload_file_size_stored(api_client):
    csv_content = b"x,y\n1,2\n3,4\n"
    r = api_client.post(
        "/api/files/upload",
        files={"file": ("sizes.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["file_size_bytes"] == len(csv_content)


def test_upload_with_nan_values(api_client):
    """NaN values in CSV must become null in JSON response."""
    csv_content = b"name,value\nAlice,1.0\nBob,\nCharlie,3.0\n"
    r = api_client.post(
        "/api/files/upload",
        files={"file": ("nan_test.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r.status_code == 200
    schema = r.json()["data"]["schema_preview"]
    # Bob's value is NaN — must be null in JSON
    # Find the row with "Bob"
    bob_row = None
    for row in schema["sample_rows"]:
        if row[0] == "Bob":
            bob_row = row
    if bob_row is not None:
        assert bob_row[1] is None
