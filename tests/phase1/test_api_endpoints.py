"""
Phase 1 gate tests — API endpoint contract.

Covers: session persistence round-trip, dataset upload shape,
SSE streaming endpoint shape, audit log record creation.

No LLM key required for these tests (graph.runner.run_analyst is mocked
where needed so the SSE shape can be asserted independently of real
Gemini calls).
"""
import io
import json
import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from db.models import SessionRow, DatasetRow, MessageRow, QueryLogRow


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(_isolated_db):
    """FastAPI test client backed by isolated SQLite DB."""
    from fastapi.testclient import TestClient
    from api import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session_id(client):
    """Create a fresh session and return its ID."""
    r = client.post("/sessions")
    assert r.status_code == 201
    return r.json()["data"]["session_id"]


# ---------------------------------------------------------------------------
# Session persistence round-trip
# ---------------------------------------------------------------------------

class TestSessionRoundTrip:
    def test_create_and_retrieve_session(self, client):
        r = client.post("/sessions")
        assert r.status_code == 201
        sid = r.json()["data"]["session_id"]

        r2 = client.get(f"/sessions/{sid}")
        assert r2.status_code == 200
        data = r2.json()["data"]
        assert data["session_id"] == sid
        assert data["name"] == "Session 1"
        assert data["datasets"] == []
        assert data["messages"] == []

    def test_list_sessions_reflects_created(self, client):
        client.post("/sessions")
        client.post("/sessions")

        r = client.get("/sessions")
        assert r.status_code == 200
        sessions = r.json()["data"]
        assert len(sessions) == 2
        # newest first
        assert sessions[0]["name"] == "Session 2"
        assert sessions[1]["name"] == "Session 1"

    def test_session_envelope_shape(self, client):
        r = client.post("/sessions")
        body = r.json()
        assert "data" in body
        assert "error" in body
        assert body["error"] is None
        d = body["data"]
        assert "session_id" in d
        assert "name" in d
        assert "created_at" in d

    def test_get_nonexistent_session_404(self, client):
        r = client.get("/sessions/does-not-exist")
        assert r.status_code == 404
        body = r.json()
        assert body["detail"]["code"] == "SESSION_NOT_FOUND"


# ---------------------------------------------------------------------------
# Dataset upload shape
# ---------------------------------------------------------------------------

class TestDatasetUploadShape:
    def test_upload_csv_shape(self, client, session_id, tmp_path, monkeypatch):
        monkeypatch.setattr("api.datasets.UPLOAD_DIR", tmp_path)
        mock_schema = {
            "columns": [
                {"name": "region", "type": "VARCHAR"},
                {"name": "revenue", "type": "DOUBLE"},
            ],
            "row_count": 100,
            "view_name": "sales",
        }
        with patch("api.datasets.load_dataset_schema", return_value=mock_schema):
            r = client.post(
                "/datasets",
                data={"session_id": session_id},
                files={"file": ("sales.csv", io.BytesIO(b"region,revenue\nNorth,1000"), "text/csv")},
            )

        assert r.status_code == 201
        body = r.json()
        assert body["error"] is None
        d = body["data"]
        assert "dataset_id" in d
        assert d["name"] == "sales.csv"
        assert d["row_count"] == 100
        assert len(d["columns"]) == 2
        assert d["columns"][0] == {"name": "region", "type": "VARCHAR"}
        assert "uploaded_at" in d

    def test_dataset_appears_in_session_detail(self, client, session_id, tmp_path, monkeypatch):
        monkeypatch.setattr("api.datasets.UPLOAD_DIR", tmp_path)
        mock_schema = {
            "columns": [{"name": "x", "type": "INTEGER"}],
            "row_count": 5,
            "view_name": "data",
        }
        with patch("api.datasets.load_dataset_schema", return_value=mock_schema):
            client.post(
                "/datasets",
                data={"session_id": session_id},
                files={"file": ("data.csv", io.BytesIO(b"x\n1"), "text/csv")},
            )

        r = client.get(f"/sessions/{session_id}")
        data = r.json()["data"]
        assert len(data["datasets"]) == 1
        assert data["datasets"][0]["name"] == "data.csv"

    def test_upload_unsupported_type_returns_400(self, client, session_id):
        r = client.post(
            "/datasets",
            data={"session_id": session_id},
            files={"file": ("bad.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_upload_unknown_session_returns_404(self, client):
        r = client.post(
            "/datasets",
            data={"session_id": "no-such-session"},
            files={"file": ("f.csv", io.BytesIO(b"a,b"), "text/csv")},
        )
        assert r.status_code == 404

    def test_list_datasets_shape(self, client, session_id, _isolated_db):
        """Seed a dataset row directly and verify GET /datasets response."""
        with Session(_isolated_db) as s:
            ds = DatasetRow(
                session_id=session_id, name="sales.csv",
                file_path="/data/sales.csv", file_type="csv",
                row_count=50,
                columns_json=json.dumps([{"name": "date", "type": "DATE"}]),
            )
            s.add(ds)
            s.commit()

        r = client.get(f"/datasets?session_id={session_id}")
        assert r.status_code == 200
        items = r.json()["data"]
        assert len(items) == 1
        item = items[0]
        assert "dataset_id" in item
        assert item["name"] == "sales.csv"
        assert item["row_count"] == 50
        assert item["columns"] == [{"name": "date", "type": "DATE"}]
        assert "uploaded_at" in item


# ---------------------------------------------------------------------------
# SSE streaming chat endpoint shape
# ---------------------------------------------------------------------------

class TestChatSSEShape:
    def _sse_events(self, session_id, client):
        """Return list of (event_name, data_str) tuples parsed from SSE body."""
        def mock_runner(sid, question):
            yield 'event: status\ndata: {"node": "classify_intent", "message": "Analysing..."}\n\n'
            yield 'event: chunk\ndata: {"text": "The answer is 42."}\n\n'
            yield 'event: done\ndata: {"message_id": "msg-test", "status": "completed"}\n\n'

        with patch("graph.runner.run_analyst", mock_runner):
            r = client.get(
                f"/chat?session_id={session_id}&q=What+is+the+meaning+of+life",
                headers={"Accept": "text/event-stream"},
            )
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        return r.text

    def test_sse_content_type(self, client, session_id):
        def mock_runner(sid, q):
            yield 'event: done\ndata: {"message_id": "m", "status": "completed"}\n\n'

        with patch("graph.runner.run_analyst", mock_runner):
            r = client.get(f"/chat?session_id={session_id}&q=hello")

        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]

    def test_sse_response_contains_status_and_done_events(self, client, session_id):
        body = self._sse_events(session_id, client)
        assert "event: status" in body
        assert "event: done" in body
        assert '"node": "classify_intent"' in body

    def test_sse_done_event_has_message_id_and_status(self, client, session_id):
        body = self._sse_events(session_id, client)
        # Parse done event
        lines = body.split("\n")
        done_data = None
        for i, line in enumerate(lines):
            if line.strip() == "event: done" and i + 1 < len(lines):
                data_line = lines[i + 1]
                if data_line.startswith("data: "):
                    done_data = json.loads(data_line[6:])
        assert done_data is not None
        assert "message_id" in done_data
        assert "status" in done_data

    def test_blank_question_returns_400_before_stream(self, client, session_id):
        r = client.get(f"/chat?session_id={session_id}&q=   ")
        assert r.status_code == 400
        body = r.json()
        assert body["detail"]["code"] == "INVALID_QUESTION"

    def test_unknown_session_returns_404_before_stream(self, client):
        r = client.get("/chat?session_id=ghost&q=hello")
        assert r.status_code == 404
        body = r.json()
        assert body["detail"]["code"] == "SESSION_NOT_FOUND"


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class TestAuditLog:
    def test_empty_audit_log(self, client, session_id):
        r = client.get(f"/audit?session_id={session_id}")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] == 0
        assert data["entries"] == []

    def test_audit_log_shape(self, client, session_id, _isolated_db):
        """Seed a QueryLog directly and verify response shape."""
        with Session(_isolated_db) as s:
            msg = MessageRow(
                session_id=session_id, role="assistant",
                content="{}", status="completed",
            )
            s.add(msg)
            s.flush()
            ql = QueryLogRow(
                session_id=session_id,
                message_id=msg.id,
                dataset_name="sales.csv",
                sql="SELECT region, SUM(revenue) FROM sales GROUP BY 1",
                row_count=5,
                latency_ms=42,
            )
            s.add(ql)
            s.commit()

        r = client.get(f"/audit?session_id={session_id}")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] == 1
        entry = data["entries"][0]
        assert "query_log_id" in entry
        assert entry["dataset_name"] == "sales.csv"
        assert "SELECT" in entry["sql"]
        assert entry["row_count"] == 5
        assert entry["latency_ms"] == 42
        assert entry["error"] is None
        assert "created_at" in entry

    def test_audit_log_pagination(self, client, session_id, _isolated_db):
        with Session(_isolated_db) as s:
            msg = MessageRow(
                session_id=session_id, role="assistant",
                content="{}", status="completed",
            )
            s.add(msg)
            s.flush()
            for i in range(10):
                s.add(QueryLogRow(
                    session_id=session_id,
                    message_id=msg.id,
                    dataset_name="d.csv",
                    sql=f"SELECT {i}",
                    row_count=i,
                ))
            s.commit()

        r = client.get(f"/audit?session_id={session_id}&limit=3&offset=0")
        data = r.json()["data"]
        assert data["total"] == 10
        assert len(data["entries"]) == 3

    def test_audit_log_unknown_session_returns_404(self, client):
        r = client.get("/audit?session_id=ghost")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# /runs stub
# ---------------------------------------------------------------------------

class TestRunsStub:
    def test_post_runs_returns_501(self, client):
        r = client.post("/runs", json={"input_text": "hello"})
        assert r.status_code == 501

    def test_get_run_returns_501(self, client):
        r = client.get("/runs/any-id")
        assert r.status_code == 501
