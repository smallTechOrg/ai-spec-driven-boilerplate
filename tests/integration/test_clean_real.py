"""Real-Gemini integration test for slice-4b C24 NL data cleaning.

Requires `AGENT_GEMINI_API_KEY` in `.env` (auto-detect selects the real Gemini
provider). This is the AUTHORITATIVE gate facet for the clean preview + apply path
— it asserts on REAL behaviour:

- `POST /datasets/{id}/clean` with "drop rows that contain any null values" returns
  non-empty REAL pandas code (no `[stub]`) and `before.rows > after.rows` (nulls
  actually dropped), and the STORED dataset is unchanged (preview runs on a copy).
- `POST /datasets/{id}/clean/apply` with the returned code updates the dataset's
  `row_count` to `after.rows` and the on-disk CSV reflects it.

Driven through the `api_client` TestClient against the production SQLite driver
(the isolated copy via the conftest `_isolated_db` fixture). The on-disk uploads
land in the real `uploads/` (upload route) — they are written/overwritten under a
fresh dataset id, so they do not collide with anything.
"""
from __future__ import annotations

import io

import pandas as pd
import pytest


def _upload(client, df: pd.DataFrame, name: str) -> str:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    files = {"file": (name, buf, "text/csv")}
    r = client.post("/upload?force=true", files=files)
    assert r.status_code == 200, r.text
    return r.json()["data"]["dataset_id"]


@pytest.mark.usefixtures("_require_llm_key")
def test_clean_preview_then_apply_real_gemini(api_client):
    # A frame with some rows that contain null/blank values.
    df = pd.DataFrame(
        {
            "name": ["alice", "bob", None, "dave", "erin"],
            "age": [30, None, 25, 40, 22],
            "city": ["london", "paris", "berlin", None, "rome"],
        }
    )
    before_nulls = int(df.isnull().any(axis=1).sum())
    assert before_nulls > 0, "fixture must contain null rows"

    ds = _upload(api_client, df, "people_with_nulls.csv")

    # --- preview ----------------------------------------------------------
    r = api_client.post(
        f"/datasets/{ds}/clean",
        json={"instruction": "drop rows that contain any null values"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    code = data["code"]

    print(f"\n[clean] generated code (first line): {code.splitlines()[0]!r}")
    print(f"[clean] before={data['before']} after={data['after']}")

    assert code and code.strip(), "preview must return non-empty pandas code"
    assert "[stub]" not in code, "got a stub reply — real provider not used"
    assert data["before"]["rows"] == 5
    # Dropping null rows must reduce the row count.
    assert data["before"]["rows"] > data["after"]["rows"], (
        f"expected nulls dropped (before > after); got {data['before']} / {data['after']} "
        f"with code {code!r}"
    )
    assert data["after"]["rows"] == 5 - before_nulls

    # The stored dataset is UNCHANGED after a preview (ran on a copy).
    g = api_client.get(f"/datasets/{ds}")
    assert g.status_code == 200, g.text
    assert g.json()["data"]["row_count"] == 5, "preview must not mutate the stored file"

    after_rows = data["after"]["rows"]

    # --- apply ------------------------------------------------------------
    a = api_client.post(f"/datasets/{ds}/clean/apply", json={"code": code})
    assert a.status_code == 200, a.text
    applied = a.json()["data"]
    assert applied["row_count"] == after_rows, (
        f"apply must persist after.rows={after_rows}; got {applied['row_count']}"
    )

    # GET reflects the new count, and the on-disk CSV does too.
    g2 = api_client.get(f"/datasets/{ds}")
    assert g2.json()["data"]["row_count"] == after_rows

    g2_path = g2.json()["data"]["file_path"]
    on_disk = pd.read_csv(g2_path)
    assert len(on_disk) == after_rows, "on-disk CSV must reflect the apply"
    print(f"[clean] applied -> stored row_count={applied['row_count']} (on-disk {len(on_disk)})")
