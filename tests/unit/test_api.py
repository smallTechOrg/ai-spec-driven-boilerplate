"""API contract tests — no LLM key required (graph is not invoked here)."""
import io
import json
from unittest.mock import patch

import pandas as pd
from sqlalchemy.orm import Session

from db.models import Dataset, RunRow
from domain.ask import AskResponse, ChartSpec, Cost, KeyStat, SummaryTable


def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_upload_csv_returns_profile(api_client):
    csv = b"region,amount\nWest,100\nEast,200\nWest,300\n"
    r = api_client.post(
        "/api/datasets",
        files={"file": ("sales.csv", io.BytesIO(csv), "text/csv")},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert len(data["datasets"]) == 1
    ds = data["datasets"][0]
    assert ds["source_kind"] == "csv"
    assert ds["row_count"] == 3
    assert ds["profile"]["row_count"] == 3
    names = {c["name"] for c in ds["profile"]["columns"]}
    assert names == {"region", "amount"}


def test_upload_excel_returns_one_dataset_per_sheet(api_client):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame({"a": [1, 2]}).to_excel(w, sheet_name="One", index=False)
        pd.DataFrame({"b": [3, 4, 5]}).to_excel(w, sheet_name="Two", index=False)
    r = api_client.post(
        "/api/datasets",
        files={"file": ("book.xlsx", io.BytesIO(buf.getvalue()),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert len(data["datasets"]) == 2


def test_upload_unsupported_type_returns_400(api_client):
    r = api_client.post(
        "/api/datasets",
        files={"file": ("data.json", io.BytesIO(b'{"a":1}'), "application/json")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "BAD_FILE"


def test_ask_unknown_dataset_returns_404(api_client):
    r = api_client.post(
        "/api/ask", json={"dataset_id": "missing", "question": "anything?"}
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_ask_missing_question_returns_400(api_client):
    r = api_client.post("/api/ask", json={"dataset_id": "x", "question": ""})
    assert r.status_code == 400


def test_ask_returns_rich_envelope(api_client, _isolated_db):
    """The ask endpoint returns the rich-answer envelope (runner stubbed)."""
    with Session(_isolated_db) as s:
        ds = Dataset(
            name="d.csv", source_path="/tmp/d.csv", source_kind="csv",
            duckdb_table="ds", row_count=3,
        )
        s.add(ds)
        s.commit()
        ds_id = ds.id

    fake = AskResponse(
        run_id="run-1",
        status="completed",
        answer="West leads.",
        key_stats=[KeyStat(label="Top region", value="West")],
        chart_spec=ChartSpec(type="bar", x="region", y="total",
                             data=[{"region": "West", "total": 400}]),
        summary_table=SummaryTable(columns=["region", "total"],
                                   rows=[["West", 400]]),
        insight="West dominates.",
        follow_ups=["Why?"],
        plan_steps=["group by region"],
        generated_sql="SELECT region, SUM(amount) total FROM ds GROUP BY region",
        cost=Cost(prompt_tokens=100, completion_tokens=50, est_usd=0.001),
    )
    with patch("api.ask.run_ask", return_value=fake):
        r = api_client.post("/api/ask", json={"dataset_id": ds_id, "question": "?"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "completed"
    assert data["answer"] == "West leads."
    assert data["key_stats"][0]["label"] == "Top region"
    assert data["chart_spec"]["type"] == "bar"
    assert data["summary_table"]["columns"] == ["region", "total"]
    assert data["cost"]["est_usd"] == 0.001
    assert data["generated_sql"].startswith("SELECT")


def test_ask_failed_run_is_200_with_attempted_sql(api_client, _isolated_db):
    """A graph failure surfaces as HTTP 200 status=failed with attempted SQL."""
    with Session(_isolated_db) as s:
        ds = Dataset(name="d.csv", source_path="/tmp/d.csv", source_kind="csv",
                     duckdb_table="ds")
        s.add(ds)
        s.commit()
        ds_id = ds.id

    failed = AskResponse(
        run_id="run-2",
        status="failed",
        generated_sql="SELECT broken FROM ds",
        error="Query failed: no such column: broken",
    )
    with patch("api.ask.run_ask", return_value=failed):
        r = api_client.post("/api/ask", json={"dataset_id": ds_id, "question": "?"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "failed"
    assert data["generated_sql"] == "SELECT broken FROM ds"
    assert "broken" in data["error"]


def test_get_run_not_found(api_client):
    r = api_client.get("/api/runs/nonexistent-id")
    assert r.status_code == 404


def test_list_runs_returns_persisted_runs(api_client, _isolated_db):
    with Session(_isolated_db) as s:
        s.add(RunRow(question="q1", status="completed", generated_sql="SELECT 1",
                     est_usd=0.0004, dataset_id="ds1"))
        s.commit()
    r = api_client.get("/api/runs")
    assert r.status_code == 200
    runs = r.json()["data"]["runs"]
    assert len(runs) == 1
    assert runs[0]["question"] == "q1"
    assert runs[0]["generated_sql"] == "SELECT 1"


def test_get_run_detail_returns_full_record(api_client, _isolated_db):
    with Session(_isolated_db) as s:
        run = RunRow(
            question="q", status="completed",
            plan_json=json.dumps(["step a"]),
            generated_sql="SELECT 1",
            result_summary_json=json.dumps({"answer": "hi"}),
            prompt_tokens=10, completion_tokens=5, est_usd=0.0001,
        )
        s.add(run)
        s.commit()
        run_id = run.id
    r = api_client.get(f"/api/runs/{run_id}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["plan_steps"] == ["step a"]
    assert data["result_summary"]["answer"] == "hi"
    assert data["prompt_tokens"] == 10
