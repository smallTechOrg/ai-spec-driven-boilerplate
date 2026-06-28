"""Phase 2 integration: follow-up suggestions after a successful run.

Drives the full upload -> ask -> run path against the REAL Gemini API (skipped
without a key) and asserts 2-3 follow-ups are produced, persisted to
runs.followups_json, present in the SSE `final` event, and on GET /runs/{id}.
Also asserts schema-only privacy and graceful degradation on LLM failure.
"""
import io
import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from db.models import DatasetRow, RunRow
from analyst.profile import profile_csv
from graph.runner import run_agent

OLIST = (
    Path(__file__).resolve().parent.parent.parent
    / "src" / "data" / "datasets"
    / "8bc76e9e-1151-437e-95eb-727b57b674ee"
    / "olist_orders_dataset.csv"
)
QUESTION = "How many orders are there for each order_status?"


def _seed_dataset(engine, path: Path) -> str:
    prof = profile_csv(str(path))
    with Session(engine) as s:
        ds = DatasetRow(
            filename=path.name,
            path=str(path),
            row_count=prof.row_count,
            schema_json=json.dumps(prof.schema),
            sample_json=json.dumps(prof.sample_rows),
        )
        s.add(ds)
        s.commit()
        return ds.id


@pytest.mark.usefixtures("_require_llm_key")
def test_followups_persisted_real_gemini(_isolated_db):
    assert OLIST.exists(), f"sample CSV missing at {OLIST}"
    dataset_id = _seed_dataset(_isolated_db, OLIST)

    run_id = run_agent(dataset_id, QUESTION)

    with Session(_isolated_db) as s:
        run = s.get(RunRow, run_id)

    assert run is not None
    assert run.status == "completed", run.error_message
    assert run.followups_json, "followups_json must be persisted"
    followups = json.loads(run.followups_json)
    assert isinstance(followups, list)
    assert 2 <= len(followups) <= 3, f"expected 2-3 follow-ups, got {followups}"
    assert all(isinstance(f, str) and f.strip() for f in followups)


@pytest.mark.usefixtures("_require_llm_key")
def test_followups_in_stream_and_get_run(api_client, _isolated_db):
    """HTTP round-trip: the `final` SSE event and GET /runs/{id} both carry the
    follow-ups (the seam the frontend consumes)."""
    with OLIST.open("rb") as fh:
        data = fh.read()
    up = api_client.post(
        "/datasets", files={"file": (OLIST.name, io.BytesIO(data), "text/csv")},
    )
    assert up.status_code == 200, up.text
    dataset_id = up.json()["data"]["dataset_id"]

    created = api_client.post(f"/datasets/{dataset_id}/runs", json={"question": QUESTION})
    assert created.status_code == 200
    run_id = created.json()["data"]["run_id"]

    final_payload = None
    with api_client.stream("GET", f"/runs/{run_id}/stream") as resp:
        assert resp.status_code == 200
        cur_event, cur_data = None, None
        for line in resp.iter_lines():
            if line.startswith("event:"):
                cur_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                cur_data = line.split(":", 1)[1].strip()
                if cur_event == "final":
                    final_payload = json.loads(cur_data)
                    break
                if cur_event == "error":
                    pytest.fail(f"run failed: {cur_data}")

    assert final_payload is not None, "no final event received"
    assert "followups" in final_payload, "final event must carry followups"
    assert 2 <= len(final_payload["followups"]) <= 3

    fetched = api_client.get(f"/runs/{run_id}")
    assert fetched.status_code == 200
    body = fetched.json()["data"]
    assert "followups" in body
    assert 2 <= len(body["followups"]) <= 3
    assert body["followups"] == final_payload["followups"]


def test_followups_degrade_on_llm_failure(_isolated_db, monkeypatch):
    """A follow-ups LLM failure must NOT fail the run — followups become []."""
    import graph.nodes as nodes
    from llm.client import LLMClient as _RealLLMClient

    dataset_id = _seed_dataset(_isolated_db, OLIST)

    # Deterministic fake: real plan/code so the run completes, but the
    # follow-ups call (schema-only system prompt) raises.
    good_code = (
        "counts = df['order_status'].value_counts()\n"
        "result = counts.to_dict()\n"
        "chart = {'type': 'bar', 'x': list(counts.index), "
        "'y': [int(v) for v in counts.values]}\n"
        "table = counts.reset_index()\n"
    )

    class _Fake:
        def call_model_with_usage(self, prompt, *, system=None):
            sys = (system or "").lower()
            if "follow-up" in sys or "followup" in sys:
                raise RuntimeError("gemini down for followups")
            if "short plan" in prompt.lower() or "plan" in sys:
                return "Group by order_status and count.", 5
            return f"```python\n{good_code}\n```", 10

    def _factory():
        c = object.__new__(_RealLLMClient)
        c._provider = _Fake()
        return c

    monkeypatch.setattr(nodes, "LLMClient", _factory)

    run_id = run_agent(dataset_id, QUESTION)
    with Session(_isolated_db) as s:
        run = s.get(RunRow, run_id)

    assert run.status == "completed", run.error_message
    assert json.loads(run.followups_json) == []  # degraded, run still succeeded
