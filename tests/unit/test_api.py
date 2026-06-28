"""API contract tests that do not invoke the LLM."""
import io


def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_upload_rejects_non_csv(api_client):
    r = api_client.post(
        "/api/datasets", files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")}
    )
    assert r.status_code == 400


def test_upload_rejects_empty_file(api_client):
    r = api_client.post(
        "/api/datasets", files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    )
    assert r.status_code == 400


def test_upload_profiles_csv(api_client, tmp_path, monkeypatch):
    import config.settings as m
    m._settings = None
    monkeypatch.setenv("AGENT_DATA_DIR", str(tmp_path))
    csv = b"region,order_value\nWest,10\nEast,20\n"
    r = api_client.post(
        "/api/datasets", files={"file": ("o.csv", io.BytesIO(csv), "text/csv")}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["row_count"] == 2
    assert body["column_count"] == 2


def test_analyze_unknown_dataset_404(api_client):
    r = api_client.post(
        "/api/analyses", json={"dataset_id": "nope", "question": "x?"}
    )
    assert r.status_code == 404


def test_analyze_empty_question_400(api_client):
    r = api_client.post(
        "/api/analyses", json={"dataset_id": "nope", "question": "   "}
    )
    assert r.status_code == 400


def test_get_analysis_not_found_404(api_client):
    r = api_client.get("/api/analyses/nonexistent")
    assert r.status_code == 404
