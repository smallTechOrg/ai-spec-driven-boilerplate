"""API surface — multipart upload, ask, run fetch, 404 paths. Real Gemini for ask."""
import io
import re

import pandas as pd
import pytest


def _contains_number(text: str, value: int) -> bool:
    normalized = re.sub(r"(?<=\d),(?=\d)", "", text)
    return bool(re.search(rf"(?<!\d){value}(?:\.0+)?(?!\d)", normalized))


def _csv_bytes() -> bytes:
    df = pd.DataFrame(
        {
            "region": ["North", "South", "North"],
            "revenue": [100, 250, 175],
        }
    )
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def _upload(api_client) -> dict:
    files = {"file": ("sales.csv", _csv_bytes(), "text/csv")}
    r = api_client.post("/datasets", files=files)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_upload_returns_profile(api_client):
    data = _upload(api_client)
    assert data["dataset"]["kind"] == "csv"
    assert data["dataset"]["row_count"] == 3
    assert data["dataset"]["column_count"] == 2
    assert data["profile"]["row_count"] == 3
    names = [c["name"] for c in data["profile"]["columns"]]
    assert names == ["region", "revenue"]


def test_upload_unsupported_type_400(api_client):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    r = api_client.post("/datasets", files=files)
    assert r.status_code == 400


def test_get_dataset_404(api_client):
    r = api_client.get("/datasets/does-not-exist")
    assert r.status_code == 404


def test_get_dataset_roundtrip(api_client):
    data = _upload(api_client)
    dataset_id = data["dataset"]["id"]
    r = api_client.get(f"/datasets/{dataset_id}")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["dataset"]["id"] == dataset_id


def test_ask_unknown_dataset_404(api_client):
    r = api_client.post("/datasets/nope/ask", json={"question": "anything?"})
    assert r.status_code == 404


def test_get_run_404(api_client):
    r = api_client.get("/runs/nope")
    assert r.status_code == 404


@pytest.mark.usefixtures("_require_llm_key")
def test_ask_and_fetch_run(api_client):
    data = _upload(api_client)
    dataset_id = data["dataset"]["id"]

    r = api_client.post(
        f"/datasets/{dataset_id}/ask",
        json={"question": "What is the total revenue across all rows?"},
    )
    assert r.status_code == 200, r.text
    run = r.json()["data"]["run"]
    assert run["status"] == "completed", run.get("error_message")
    assert run["answer"]
    assert run["code"]
    assert run["tokens"]["total"] > 0
    assert run["cost_usd"] > 0
    assert _contains_number(run["answer"], 525), run["answer"]  # 100+250+175

    run_id = run["id"]
    r2 = api_client.get(f"/runs/{run_id}")
    assert r2.status_code == 200
    persisted = r2.json()["data"]["run"]
    assert persisted["id"] == run_id
    assert persisted["code"] == run["code"]
    assert persisted["tokens"]["total"] == run["tokens"]["total"]
