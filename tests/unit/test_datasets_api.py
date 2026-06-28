"""Dataset route tests with a mocked runner — exercises upload, SSE framing,
and the exact response envelope WITHOUT calling the LLM."""

import csv
import io
import json

from unittest.mock import patch


def _make_csv(rows: int = 20) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["region", "amount"])
    for i in range(rows):
        w.writerow(["NW" if i % 2 == 0 else "SE", i * 1.5])
    return buf.getvalue().encode()


def test_upload_returns_profile_envelope(api_client):
    r = api_client.post(
        "/datasets", files={"file": ("sales.csv", _make_csv(20), "text/csv")}
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["dataset_id"]
    assert data["name"] == "sales.csv"
    assert data["row_count"] == 20
    assert data["column_count"] == 2
    names = {c["name"] for c in data["profile"]}
    assert {"region", "amount"} <= names
    assert isinstance(data["sample_rows"], list) and data["sample_rows"]


def _fake_run_ask(dataset_id, conversation_id, question, on_step):
    # Emit a couple of live step events, then return the data envelope.
    on_step("plan", "running")
    on_step("plan", "done")
    on_step("execute_local", "done")
    return {
        "turn_id": "turn-1",
        "conversation_id": conversation_id or "conv-1",
        "answer": "NW had more.",
        "plan": ["group by region"],
        "code": "df.groupby('region').size()",
        "result_table": [{"region": "NW", "count": 10}],
        "chart_spec": {"chart_type": "bar", "x": "region", "y": "count"},
        "follow_ups": ["Which region grew fastest?"],
        "token_usage": {"prompt": 100, "completion": 20, "total": 120},
        "estimated_cost_usd": 0.0004,
        "assumptions": [],
    }


def test_ask_streams_steps_then_final_envelope(api_client):
    up = api_client.post(
        "/datasets", files={"file": ("sales.csv", _make_csv(20), "text/csv")}
    )
    dataset_id = up.json()["data"]["dataset_id"]

    with patch("api.datasets.run_ask", side_effect=_fake_run_ask):
        r = api_client.post(
            f"/datasets/{dataset_id}/ask", json={"question": "per region?"}
        )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]

    frames = [f for f in r.text.split("\n\n") if f.strip()]
    payloads = [json.loads(f[len("data: ") :]) for f in frames]

    steps = [p for p in payloads if "step" in p]
    assert {"step": "plan", "status": "running"} in steps
    assert {"step": "execute_local", "status": "done"} in steps

    finals = [p for p in payloads if "data" in p]
    assert len(finals) == 1
    data = finals[0]["data"]
    # Exact frontend contract shape.
    assert data["turn_id"] == "turn-1"
    assert data["answer"] == "NW had more."
    assert data["result_table"] == [{"region": "NW", "count": 10}]
    assert data["token_usage"] == {"prompt": 100, "completion": 20, "total": 120}
    assert data["chart_spec"]["chart_type"] == "bar"
