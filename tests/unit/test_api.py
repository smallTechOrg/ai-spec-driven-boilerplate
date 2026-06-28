"""API contract tests — no LLM key required, graph is not invoked."""


def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_ask_unknown_dataset_404(api_client):
    r = api_client.post("/datasets/nonexistent/ask", json={"question": "hi"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "DATASET_NOT_FOUND"


def test_ask_missing_question_422(api_client):
    # Body present but no question field → pydantic 422.
    r = api_client.post("/datasets/whatever/ask", json={"conversation_id": None})
    assert r.status_code == 422


def test_ask_blank_question_422(api_client):
    r = api_client.post("/datasets/whatever/ask", json={"question": "   "})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "MISSING_QUESTION"


def test_upload_empty_file_400(api_client):
    r = api_client.post("/datasets", files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "EMPTY_FILE"


def test_upload_unparseable_file_400(api_client):
    # A single blank line yields a frame with no columns → unparseable.
    r = api_client.post("/datasets", files={"file": ("bad.csv", b"\n", "text/csv")})
    assert r.status_code == 400
