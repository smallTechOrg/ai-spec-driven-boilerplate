"""Integration tests for multi-file upload and Excel (.xlsx) support."""

import io
import json
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Additional fixtures (local to this test file)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_xlsx(tmp_path):
    """Creates a small .xlsx file with columns [region, revenue, units] and 5 rows."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["region", "revenue", "units"])
    ws.append(["West", 12500.0, 120])
    ws.append(["East", 8750.5, 85])
    ws.append(["North", 6200.0, 62])
    ws.append(["South", 9800.0, 98])
    ws.append(["West", 14200.0, 140])

    p = tmp_path / "sales.xlsx"
    wb.save(str(p))
    return p


@pytest.fixture
def second_csv(tmp_path):
    """Creates a second small CSV with columns [product_id, category, price] and 5 rows."""
    csv_content = "product_id,category,price\n1,Electronics,299.99\n2,Clothing,49.99\n3,Electronics,199.99\n4,Food,9.99\n5,Clothing,89.99\n"
    p = tmp_path / "products.csv"
    p.write_text(csv_content)
    return p


# ---------------------------------------------------------------------------
# Helper: create a session via the API
# ---------------------------------------------------------------------------

def _create_session(client) -> str:
    """POST /sessions and return session_id."""
    resp = client.post("/sessions")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["data"]["session_id"]


def _upload_file(client, session_id: str, file_path: Path) -> dict:
    """Upload a file to the given session; return the full response JSON."""
    with open(file_path, "rb") as f:
        content = f.read()
    suffix = file_path.suffix.lower()
    mime = "text/csv" if suffix == ".csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    resp = client.post(
        f"/sessions/{session_id}/files",
        files={"file": (file_path.name, io.BytesIO(content), mime)},
    )
    return resp


# ---------------------------------------------------------------------------
# Test 1: Upload two CSV files to the same session
# ---------------------------------------------------------------------------

def test_upload_two_csv_files(api_client, sample_csv, second_csv):
    """Two CSV uploads to the same session must both succeed with correct profiles."""
    session_id = _create_session(api_client)

    # Upload first CSV (sales.csv: 10 rows, 4 columns)
    resp1 = _upload_file(api_client, session_id, sample_csv)
    assert resp1.status_code == 200, resp1.text
    data1 = resp1.json()["data"]
    profile1 = data1["profile"]
    assert profile1["row_count"] == 10
    assert profile1["column_count"] == 4
    assert data1["filename"] == "sales.csv"

    # Upload second CSV (products.csv: 5 rows, 3 columns)
    resp2 = _upload_file(api_client, session_id, second_csv)
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()["data"]
    profile2 = data2["profile"]
    assert profile2["row_count"] == 5
    assert profile2["column_count"] == 3
    assert data2["filename"] == "products.csv"

    # Both uploads have distinct file_ids
    assert data1["file_id"] != data2["file_id"]


# ---------------------------------------------------------------------------
# Test 2: Upload an Excel (.xlsx) file
# ---------------------------------------------------------------------------

def test_upload_xlsx_file(api_client, sample_xlsx):
    """Uploading a .xlsx file must succeed and return a valid profile."""
    session_id = _create_session(api_client)
    resp = _upload_file(api_client, session_id, sample_xlsx)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["filename"] == "sales.xlsx"
    profile = data["profile"]
    assert profile["row_count"] == 5
    assert profile["column_count"] == 3
    col_names = [c["name"] for c in profile["columns"]]
    assert "region" in col_names
    assert "revenue" in col_names
    assert "units" in col_names


# ---------------------------------------------------------------------------
# Test 3: Reject unsupported file extension
# ---------------------------------------------------------------------------

def test_upload_xlsx_rejected_if_wrong_ext(api_client, tmp_path):
    """Uploading a .txt file must return 400 INVALID_FILE."""
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("col1,col2\n1,2\n")

    session_id = _create_session(api_client)
    resp = _upload_file(api_client, session_id, txt_file)
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["error"]["code"] == "INVALID_FILE"
    assert "xlsx" in body["error"]["message"].lower() or "csv" in body["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Test 4: Both files are available in the execution context
# ---------------------------------------------------------------------------

def test_multifile_both_in_exec_context(api_client, sample_csv, second_csv, _require_llm_key):
    """After uploading 2 CSVs, a question referencing both stems must get a 200 answer."""
    session_id = _create_session(api_client)

    _upload_file(api_client, session_id, sample_csv)
    _upload_file(api_client, session_id, second_csv)

    resp = api_client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "How many rows are in each dataset? List them."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data.get("content") or data.get("answer"), "Response must have non-empty content"
    content = data.get("content") or data.get("answer")
    assert len(content.strip()) > 0


# ---------------------------------------------------------------------------
# Test 5: XLSX numeric column stats are present
# ---------------------------------------------------------------------------

def test_profile_xlsx_numeric_stats(api_client, sample_xlsx):
    """Profile of an .xlsx file with a numeric column must include stats.min/max/mean."""
    session_id = _create_session(api_client)
    resp = _upload_file(api_client, session_id, sample_xlsx)
    assert resp.status_code == 200, resp.text
    profile = resp.json()["data"]["profile"]

    # Find the 'revenue' column (numeric)
    revenue_col = next((c for c in profile["columns"] if c["name"] == "revenue"), None)
    assert revenue_col is not None, "Expected 'revenue' column in profile"
    assert "stats" in revenue_col, "Numeric column must have stats"
    stats = revenue_col["stats"]
    assert stats["min"] is not None
    assert stats["max"] is not None
    assert stats["mean"] is not None
    # Sanity check against known fixture data
    assert stats["min"] == pytest.approx(6200.0, rel=1e-3)
    assert stats["max"] == pytest.approx(14200.0, rel=1e-3)
