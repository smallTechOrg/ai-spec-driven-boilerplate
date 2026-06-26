import io
import json
import pytest

SAMPLE_CSV = """Month,Region,Revenue
Jan,North,52400
Feb,North,49000
Jan,South,38200
Feb,South,41000
Jan,West,61700
"""


@pytest.fixture
def session_id(api_client):
    resp = api_client.post("/sessions")
    assert resp.status_code == 200
    return resp.json()["data"]["session_id"]


@pytest.fixture
def dataset_id(api_client, session_id):
    resp = api_client.post(
        f"/sessions/{session_id}/datasets",
        files={"file": ("sales.csv", SAMPLE_CSV.encode(), "text/csv")},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["dataset_id"]


def test_create_session(api_client):
    resp = api_client.post("/sessions")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "session_id" in data
    assert len(data["session_id"]) > 0


def test_upload_csv(api_client, session_id):
    resp = api_client.post(
        f"/sessions/{session_id}/datasets",
        files={"file": ("sales.csv", SAMPLE_CSV.encode(), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["filename"] == "sales.csv"
    assert data["row_count"] == 5
    assert "Month" in data["column_names"]
    assert "Revenue" in data["column_names"]


def test_upload_non_csv(api_client, session_id):
    resp = api_client.post(
        f"/sessions/{session_id}/datasets",
        files={"file": ("data.xlsx", b"fake excel", "application/vnd.ms-excel")},
    )
    assert resp.status_code == 422


def test_list_datasets(api_client, session_id, dataset_id):
    resp = api_client.get(f"/sessions/{session_id}/datasets")
    assert resp.status_code == 200
    datasets = resp.json()["data"]["datasets"]
    assert len(datasets) == 1
    assert datasets[0]["dataset_id"] == dataset_id


def test_query_empty_question(api_client, session_id, dataset_id):
    resp = api_client.post(
        f"/sessions/{session_id}/queries",
        json={"question": "   ", "dataset_id": dataset_id},
    )
    assert resp.status_code == 422


def test_query_nonexistent_dataset(api_client, session_id):
    resp = api_client.post(
        f"/sessions/{session_id}/queries",
        json={"question": "What are the columns?", "dataset_id": "nonexistent-id"},
    )
    assert resp.status_code == 404


def test_query_nonexistent_session(api_client):
    resp = api_client.post(
        "/sessions/nonexistent-session/queries",
        json={"question": "What are the columns?", "dataset_id": "some-id"},
    )
    assert resp.status_code == 404


def test_upload_to_nonexistent_session(api_client):
    resp = api_client.post(
        "/sessions/nonexistent-session/datasets",
        files={"file": ("sales.csv", SAMPLE_CSV.encode(), "text/csv")},
    )
    assert resp.status_code == 404


def test_health(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200


def test_get_run_not_found(api_client):
    resp = api_client.get("/runs/nonexistent-run-id")
    assert resp.status_code == 404


def test_post_runs_deprecated(api_client):
    resp = api_client.post("/runs", json={"input_text": "hello"})
    assert resp.status_code == 400


def test_full_pipeline_real_gemini(api_client, session_id, _require_llm_key):
    """End-to-end: upload CSV -> ask question -> get text answer."""
    # Upload
    upload_resp = api_client.post(
        f"/sessions/{session_id}/datasets",
        files={"file": ("sales.csv", SAMPLE_CSV.encode(), "text/csv")},
    )
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["data"]["dataset_id"]

    # Query — use a reliable structural question
    query_resp = api_client.post(
        f"/sessions/{session_id}/queries",
        json={
            "question": "What columns are in this dataset and how many rows does it have?",
            "dataset_id": dataset_id,
        },
    )
    assert query_resp.status_code == 200
    result = query_resp.json()["data"]
    assert result["status"] == "completed"
    assert result["answer_text"]
    # Answer must mention the column names or row count
    answer = result["answer_text"].lower()
    assert any(col.lower() in answer for col in ["month", "region", "revenue"])


def test_pipeline_aggregation_query_with_table(api_client, session_id, _require_llm_key):
    """Query that should produce a table_json block — tests extract_table node."""
    upload_resp = api_client.post(
        f"/sessions/{session_id}/datasets",
        files={"file": ("sales.csv", SAMPLE_CSV.encode(), "text/csv")},
    )
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["data"]["dataset_id"]

    query_resp = api_client.post(
        f"/sessions/{session_id}/queries",
        json={
            "question": "What is the total revenue by region? Show me a table.",
            "dataset_id": dataset_id,
        },
    )
    assert query_resp.status_code == 200
    result = query_resp.json()["data"]
    assert result["status"] == "completed"
    assert result["answer_text"]
    # table_data may or may not be present depending on Gemini's response
    if result["table_data"] is not None:
        assert isinstance(result["table_data"], list)
        assert len(result["table_data"]) > 0


def test_get_run_after_query(api_client, session_id, _require_llm_key):
    """After a query, GET /runs/{run_id} must return the stored result."""
    upload_resp = api_client.post(
        f"/sessions/{session_id}/datasets",
        files={"file": ("sales.csv", SAMPLE_CSV.encode(), "text/csv")},
    )
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["data"]["dataset_id"]

    query_resp = api_client.post(
        f"/sessions/{session_id}/queries",
        json={"question": "How many rows are there?", "dataset_id": dataset_id},
    )
    assert query_resp.status_code == 200
    run_id = query_resp.json()["data"]["run_id"]

    get_resp = api_client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 200
    run_data = get_resp.json()["data"]
    assert run_data["run_id"] == run_id
    assert run_data["status"] == "completed"
