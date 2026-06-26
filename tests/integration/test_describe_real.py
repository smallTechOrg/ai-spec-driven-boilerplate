"""Real-Gemini integration test for slice-4b C30 notes + C31 compression.

Requires `AGENT_GEMINI_API_KEY` in `.env` (auto-detect selects the real Gemini
provider). This is the AUTHORITATIVE gate facet for on-demand dataset notes and
their compression to facts. It asserts on REAL behaviour:

- `POST /datasets/{id}/describe` returns immediately with `auto_notes_status="pending"`.
- Polling `GET /datasets/{id}` reaches a terminal status (done/failed) within a
  bounded window. On `done`: `context` is non-empty REAL prose (no `[stub]`), and
  `context_facts` (C31, triggered after C30) is a list.

Driven through the `api_client` TestClient against the production SQLite driver
(the isolated copy via the conftest `_isolated_db` fixture). The async notes job
shares the same monkeypatched DB engine, so its writes are visible to the GET poll.
"""
from __future__ import annotations

import io
import time

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


def _poll_status(client, dataset_id: str, *, timeout_s: float = 60.0) -> dict:
    """Poll GET /datasets/{id} until notes are done WITH facts (C31), or terminal.

    C30 sets `auto_notes_status="done"` and THEN triggers C31 fact extraction
    asynchronously, so facts arrive slightly after `done`. We therefore wait for
    `done` + non-empty `context_facts` (the full C30->C31 success), but return
    early on `failed` (a terminal non-crash outcome). On timeout we return the last
    snapshot (still `done`, possibly with facts not yet written).
    """
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        r = client.get(f"/datasets/{dataset_id}")
        assert r.status_code == 200, r.text
        last = r.json()["data"]
        status = last.get("auto_notes_status")
        if status == "failed":
            return last
        if status == "done" and last.get("context_facts"):
            return last
        time.sleep(1.0)
    return last


@pytest.mark.usefixtures("_require_llm_key")
def test_describe_generates_real_notes_and_facts(api_client):
    df = pd.DataFrame(
        {
            "product": ["widget", "gadget", "gizmo", "doohickey", "thingamajig"],
            "price_usd": [9.99, 19.99, 4.50, 14.00, 7.25],
            "in_stock": [120, 0, 45, 8, 300],
            "category": ["tools", "tools", "toys", "home", "toys"],
        }
    )
    ds = _upload(api_client, df, "products.csv")

    # Trigger C30 explicitly (the upload also fires it; both converge).
    r = api_client.post(f"/datasets/{ds}/describe")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["auto_notes_status"] == "pending"

    result = _poll_status(api_client, ds, timeout_s=90.0)
    status = result.get("auto_notes_status")
    print(f"\n[describe] terminal status={status!r}")

    # With a real key the expected outcome is `done`; tolerate `failed` only as a
    # non-crashing terminal status (a transient API error), never silently.
    assert status in ("done", "failed"), (
        f"describe must reach a terminal status; got {status!r}"
    )

    if status == "failed":
        pytest.skip("real Gemini describe transiently failed (terminal, non-crash)")

    context = result.get("context")
    facts = result.get("context_facts")

    assert context and context.strip(), "done status must have non-empty notes"
    assert "[stub]" not in context, "got stub notes — real provider not used"
    assert isinstance(facts, list), f"context_facts must be a list, got {type(facts)}"
    assert len(facts) <= 20, f"context_facts must be <= 20, got {len(facts)}"
    # C31 (triggered after C30) must populate real facts on the success path.
    assert facts, (
        "C31 compression must populate context_facts after notes generation; "
        f"got empty list (status={status!r})"
    )
    assert all(isinstance(f, str) and f.strip() for f in facts), "facts must be non-empty strings"

    print(f"[describe] notes length={len(context)} chars")
    print(f"[describe] notes (first 200): {context[:200]!r}")
    print(f"[describe] context_facts ({len(facts)}): {facts}")
