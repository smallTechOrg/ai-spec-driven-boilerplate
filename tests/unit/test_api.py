"""API contract tests that need no LLM key (graph not invoked)."""


def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_get_dataset_not_found(api_client):
    r = api_client.get("/datasets/nonexistent-id")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_ask_empty_question_rejected(api_client):
    r = api_client.post("/ask", json={"dataset_id": "x", "question": "  "})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "BAD_REQUEST"


def test_ask_unknown_dataset(api_client):
    r = api_client.post("/ask", json={"dataset_id": "nope", "question": "how many rows?"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_upload_non_csv_rejected(api_client):
    r = api_client.post(
        "/datasets",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "BAD_UPLOAD"


def test_upload_unparseable_csv(api_client):
    # A .csv name but binary garbage that pandas cannot parse as a table.
    bad = b"\x00\x01\x02\x03" * 10
    r = api_client.post(
        "/datasets",
        files={"file": ("broken.csv", bad, "text/csv")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "BAD_UPLOAD"
