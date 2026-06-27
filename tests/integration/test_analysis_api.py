"""Integration tests for the analysis-api slice — REAL Gemini key (loads .env).

The golden-path UI/API smoke for Phase 1, exercised through the FastAPI
TestClient over the real HTTP surface:

  * POST /datasets       — multipart upload of tests/fixtures/sales.csv.
  * POST /datasets/{id}/ask — the real plan -> execute -> explain graph.

These hit the real LLM; the LLM-backed cases are skipped only if no provider
key is configured. The non-LLM cases (404, 400, BAD_FILE) always run.

Known fixture facts (hand-computed over sales.csv, 16 rows):
  * total amount = 4180.0  (region, amount, date, units columns)
"""
from pathlib import Path

import pytest

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "sales.csv"
_TOTAL_AMOUNT = 4180.0


def _column_names(schema: list[dict]) -> set[str]:
    return {col["name"] for col in schema}


def _upload_fixture(api_client) -> dict:
    with _FIXTURE.open("rb") as fh:
        resp = api_client.post(
            "/datasets",
            files={"file": ("sales.csv", fh, "text/csv")},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["error"] is None
    return body["data"]


def test_upload_returns_schema_and_rowcount(api_client):
    data = _upload_fixture(api_client)

    assert data["dataset_id"]
    assert data["filename"] == "sales.csv"
    assert data["row_count"] == 16, data
    names = _column_names(data["schema"])
    assert {"region", "amount"} <= names, names
    # sample_preview is a bounded, non-empty list of real rows.
    assert isinstance(data["sample_preview"], list)
    assert data["sample_preview"], "sample_preview must be non-empty"
    assert "region" in data["sample_preview"][0]


@pytest.mark.usefixtures("_require_llm_key")
def test_ask_total_amount_completed(api_client):
    dataset_id = _upload_fixture(api_client)["dataset_id"]

    resp = api_client.post(
        f"/datasets/{dataset_id}/ask",
        json={"question": "What is the total amount?"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["error"] is None
    data = body["data"]

    assert data["status"] == "completed", data
    assert data["query_id"]
    assert data["dataset_id"] == dataset_id

    # The numeric answer reflects the hand-computed total within tolerance.
    # The graph returns `result` as the computed value and `answer` as prose.
    haystack = f"{data['result']} {data['answer']}"
    assert "4180" in haystack.replace(",", "").replace(".0", "").replace(
        "4180.00", "4180"
    ) or _close_to_total(data["result"]), data

    # The three guarantees: code, explanation, answer all present + real.
    assert data["code"], "code must be non-empty pandas"
    assert "df" in data["code"], "code must reference the dataframe"
    assert data["explanation"], "explanation must be non-empty"
    assert data["answer"], "answer must be non-empty"
    # Audit fields present.
    assert data["model"], "the answering model must be recorded"


def _close_to_total(result) -> bool:
    try:
        return abs(float(result) - _TOTAL_AMOUNT) <= 1e-6 * max(1.0, _TOTAL_AMOUNT)
    except (TypeError, ValueError):
        return False


def test_ask_unknown_dataset_404(api_client):
    resp = api_client.post(
        "/datasets/does-not-exist/ask",
        json={"question": "What is the total amount?"},
    )
    assert resp.status_code == 404, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "NOT_FOUND", detail


def test_ask_empty_question_400(api_client):
    # First upload a real dataset so the 400 is about the question, not the id.
    dataset_id = _upload_fixture(api_client)["dataset_id"]

    resp = api_client.post(
        f"/datasets/{dataset_id}/ask",
        json={"question": "   "},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "BAD_REQUEST", detail


def test_upload_non_csv_bad_file_400(api_client):
    # Garbage bytes named .csv that pandas cannot parse into columns.
    bad_bytes = b"\x00\x01\x02 this is not a csv \xff\xfe"
    resp = api_client.post(
        "/datasets",
        files={"file": ("notes.csv", bad_bytes, "text/csv")},
    )
    # Either the unparseable content (BAD_FILE) is the contract here.
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "BAD_FILE", detail


def test_upload_wrong_extension_bad_file_400(api_client):
    resp = api_client.post(
        "/datasets",
        files={"file": ("report.txt", b"region,amount\nWest,1", "text/plain")},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "BAD_FILE", detail
