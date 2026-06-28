"""TestClient end-to-end API tests for Phase-1 (real Gemini for /ask)."""
import io

import pytest


@pytest.fixture
def isolated_uploads(tmp_path, monkeypatch):
    import api.datasets as datasets_module
    monkeypatch.setattr(datasets_module, "_UPLOAD_ROOT", tmp_path / "uploads")
    return tmp_path


def _csv_bytes() -> bytes:
    lines = ["region,revenue"]
    # First 5 rows West only (sample window); bulk adds East so full != sample.
    for _ in range(5):
        lines.append("West,1")
    for i in range(2000):
        lines.append(f"{'West' if i % 2 == 0 else 'East'},10")
    return ("\n".join(lines)).encode()


def test_upload_returns_profile(api_client, isolated_uploads):
    r = api_client.post(
        "/datasets",
        files={"file": ("sales.csv", io.BytesIO(_csv_bytes()), "text/csv")},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["file_type"] == "csv"
    assert data["row_count"] == 2005
    profile = data["profile"]
    names = {c["name"] for c in profile["columns"]}
    assert names == {"region", "revenue"}
    assert "revenue" in profile["numeric_stats"]
    assert len(profile["sample"]) <= 5


def test_get_dataset_roundtrip(api_client, isolated_uploads):
    r = api_client.post(
        "/datasets",
        files={"file": ("sales.csv", io.BytesIO(_csv_bytes()), "text/csv")},
    )
    dataset_id = r.json()["data"]["id"]
    g = api_client.get(f"/datasets/{dataset_id}")
    assert g.status_code == 200
    assert g.json()["data"]["id"] == dataset_id


@pytest.mark.usefixtures("_require_llm_key")
def test_ask_returns_answer_code_plan(api_client, isolated_uploads):
    up = api_client.post(
        "/datasets",
        files={"file": ("sales.csv", io.BytesIO(_csv_bytes()), "text/csv")},
    )
    dataset_id = up.json()["data"]["id"]

    r = api_client.post(
        "/ask",
        json={"dataset_id": dataset_id, "question": "What is the total revenue by region?"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["status"] == "completed"
    assert data["answer"]
    assert data["code"]
    assert data["plan"]
    assert data["conversation_id"]
    # Phase-1 contract: charts/clarify are not produced yet.
    assert data["chart_spec"] is None
    assert data["clarifying_question"] is None
