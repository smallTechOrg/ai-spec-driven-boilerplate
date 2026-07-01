"""API contract tests — no LLM key required."""


def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_create_session(api_client):
    r = api_client.post("/sessions")
    assert r.status_code == 200
    d = r.json()["data"]
    assert "session_id" in d
    assert "created_at" in d


def test_delete_nonexistent_session(api_client):
    r = api_client.delete("/sessions/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_upload_to_nonexistent_session(api_client, sample_csv):
    with open(sample_csv, "rb") as f:
        r = api_client.post(
            "/sessions/no-such-session/files",
            files={"file": ("sales.csv", f, "text/csv")},
        )
    assert r.status_code == 404


def test_message_without_session(api_client):
    r = api_client.post("/sessions/no-such-session/messages", json={"content": "hello"})
    assert r.status_code == 404


def test_message_without_file(api_client):
    r = api_client.post("/sessions", json={})
    sid = r.json()["data"]["session_id"]
    r2 = api_client.post(f"/sessions/{sid}/messages", json={"content": "hello"})
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "NO_FILES"


def test_upload_non_csv(api_client, tmp_path):
    r = api_client.post("/sessions", json={})
    sid = r.json()["data"]["session_id"]
    p = tmp_path / "data.json"
    p.write_text('{"key": "value"}')
    with open(p, "rb") as f:
        r2 = api_client.post(
            f"/sessions/{sid}/files",
            files={"file": ("data.json", f, "application/json")},
        )
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "INVALID_FILE"


def test_get_messages_empty(api_client):
    r = api_client.post("/sessions", json={})
    sid = r.json()["data"]["session_id"]
    r2 = api_client.get(f"/sessions/{sid}/messages")
    assert r2.status_code == 200
    assert r2.json()["data"]["messages"] == []


def test_upload_csv_returns_profile(api_client, sample_csv):
    r = api_client.post("/sessions", json={})
    sid = r.json()["data"]["session_id"]
    with open(sample_csv, "rb") as f:
        r2 = api_client.post(
            f"/sessions/{sid}/files",
            files={"file": ("sales.csv", f, "text/csv")},
        )
    assert r2.status_code == 200
    data = r2.json()["data"]
    assert data["filename"] == "sales.csv"
    profile = data["profile"]
    assert profile["row_count"] == 10
    assert profile["column_count"] == 4
    col_names = [c["name"] for c in profile["columns"]]
    assert "region" in col_names
    assert "revenue" in col_names


def test_upload_csv_profile_no_raw_rows(api_client, sample_csv):
    """Privacy: profile must not contain raw row data."""
    r = api_client.post("/sessions", json={})
    sid = r.json()["data"]["session_id"]
    with open(sample_csv, "rb") as f:
        r2 = api_client.post(
            f"/sessions/{sid}/files",
            files={"file": ("sales.csv", f, "text/csv")},
        )
    profile = r2.json()["data"]["profile"]
    # Profile should have stats, not a dump of all rows
    assert "row_count" in profile
    assert "columns" in profile
    assert "data" not in profile  # no raw data array


def test_delete_session(api_client):
    r = api_client.post("/sessions", json={})
    sid = r.json()["data"]["session_id"]
    r2 = api_client.delete(f"/sessions/{sid}")
    assert r2.status_code == 200
    assert r2.json()["data"]["deleted"] is True
