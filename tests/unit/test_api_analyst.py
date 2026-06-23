"""API contract tests for the analyst agent endpoints — no LLM key required."""
import io
import json
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from db.models import SessionRow, DatasetRow, MessageRow, QueryLogRow


# ---------------------------------------------------------------------------
# /sessions
# ---------------------------------------------------------------------------

class TestCreateSession:
    def test_creates_session_returns_201(self, api_client):
        r = api_client.post("/sessions")
        assert r.status_code == 201
        data = r.json()
        assert data["error"] is None
        assert "session_id" in data["data"]
        assert data["data"]["name"] == "Session 1"
        assert "created_at" in data["data"]

    def test_session_name_increments(self, api_client):
        r1 = api_client.post("/sessions")
        r2 = api_client.post("/sessions")
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["data"]["name"] == "Session 1"
        assert r2.json()["data"]["name"] == "Session 2"

    def test_session_ids_are_unique(self, api_client):
        r1 = api_client.post("/sessions")
        r2 = api_client.post("/sessions")
        assert r1.json()["data"]["session_id"] != r2.json()["data"]["session_id"]


class TestListSessions:
    def test_empty_list(self, api_client):
        r = api_client.get("/sessions")
        assert r.status_code == 200
        data = r.json()
        assert data["error"] is None
        assert data["data"] == []

    def test_lists_sessions_newest_first(self, api_client, _isolated_db):
        # Create two sessions directly in DB with specific ordering
        with Session(_isolated_db) as s:
            from datetime import datetime, timezone
            s1 = SessionRow(name="Session 1")
            s2 = SessionRow(name="Session 2")
            s.add(s1)
            s.flush()
            s.add(s2)
            s.commit()
            id1, id2 = s1.id, s2.id

        r = api_client.get("/sessions")
        assert r.status_code == 200
        sessions = r.json()["data"]
        assert len(sessions) == 2
        # newest first — s2 was created after s1
        assert sessions[0]["session_id"] == id2
        assert sessions[1]["session_id"] == id1

    def test_includes_counts(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.flush()
            ds = DatasetRow(
                session_id=sess.id, name="foo.csv",
                file_path="/tmp/foo.csv", file_type="csv",
                row_count=10, columns_json="[]",
            )
            msg = MessageRow(session_id=sess.id, role="user", content="hello")
            s.add(ds)
            s.add(msg)
            s.commit()
            sess_id = sess.id

        r = api_client.get("/sessions")
        sessions = r.json()["data"]
        found = next(x for x in sessions if x["session_id"] == sess_id)
        assert found["dataset_count"] == 1
        assert found["message_count"] == 1


class TestGetSession:
    def test_not_found_returns_404(self, api_client):
        r = api_client.get("/sessions/nonexistent-id")
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "SESSION_NOT_FOUND"

    def test_returns_session_with_datasets_and_messages(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.flush()
            ds = DatasetRow(
                session_id=sess.id, name="sales.csv",
                file_path="/data/sales.csv", file_type="csv",
                row_count=100,
                columns_json=json.dumps([{"name": "date", "type": "DATE"}]),
            )
            msg = MessageRow(
                session_id=sess.id, role="user", content="What are the totals?",
            )
            s.add(ds)
            s.add(msg)
            s.commit()
            sess_id = sess.id

        r = api_client.get(f"/sessions/{sess_id}")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["session_id"] == sess_id
        assert len(data["datasets"]) == 1
        assert data["datasets"][0]["name"] == "sales.csv"
        assert data["datasets"][0]["columns"] == [{"name": "date", "type": "DATE"}]
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "What are the totals?"


class TestSessionStubs:
    def test_patch_session_returns_501(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.commit()
            sess_id = sess.id

        r = api_client.patch(f"/sessions/{sess_id}", json={"name": "New Name"})
        assert r.status_code == 501

    def test_delete_session_returns_501(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.commit()
            sess_id = sess.id

        r = api_client.delete(f"/sessions/{sess_id}")
        assert r.status_code == 501


# ---------------------------------------------------------------------------
# /datasets
# ---------------------------------------------------------------------------

class TestUploadDataset:
    def _make_csv_file(self, content: str = "a,b\n1,2\n3,4\n"):
        return ("test.csv", io.BytesIO(content.encode()), "text/csv")

    def test_upload_csv_returns_201(self, api_client, _isolated_db, tmp_path, monkeypatch):
        """Upload a CSV — mocks DuckDB loader so no real file I/O needed."""
        from pathlib import Path

        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.commit()
            sess_id = sess.id

        # Patch the upload dir and the loader
        monkeypatch.setattr("api.datasets.UPLOAD_DIR", tmp_path)
        mock_schema = {
            "columns": [{"name": "a", "type": "INTEGER"}, {"name": "b", "type": "INTEGER"}],
            "row_count": 2,
            "view_name": "test",
        }
        with patch("api.datasets.load_dataset_schema", return_value=mock_schema):
            r = api_client.post(
                "/datasets",
                data={"session_id": sess_id},
                files={"file": self._make_csv_file()},
            )

        assert r.status_code == 201
        data = r.json()
        assert data["error"] is None
        assert data["data"]["name"] == "test.csv"
        assert data["data"]["row_count"] == 2
        assert len(data["data"]["columns"]) == 2
        assert "dataset_id" in data["data"]
        assert "uploaded_at" in data["data"]

    def test_upload_unsupported_extension_returns_400(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.commit()
            sess_id = sess.id

        r = api_client.post(
            "/datasets",
            data={"session_id": sess_id},
            files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_upload_session_not_found_returns_404(self, api_client):
        r = api_client.post(
            "/datasets",
            data={"session_id": "nonexistent-session"},
            files={"file": ("test.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")},
        )
        assert r.status_code == 404

    def test_upload_duckdb_parse_failure_returns_400(self, api_client, _isolated_db, tmp_path, monkeypatch):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.commit()
            sess_id = sess.id

        monkeypatch.setattr("api.datasets.UPLOAD_DIR", tmp_path)
        with patch("api.datasets.load_dataset_schema", side_effect=RuntimeError("DuckDB parse error")):
            r = api_client.post(
                "/datasets",
                data={"session_id": sess_id},
                files={"file": ("bad.csv", io.BytesIO(b"corrupted"), "text/csv")},
            )

        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "PARSE_ERROR"


class TestListDatasets:
    def test_empty_list(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.commit()
            sess_id = sess.id

        r = api_client.get(f"/datasets?session_id={sess_id}")
        assert r.status_code == 200
        assert r.json()["data"] == []

    def test_lists_datasets(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.flush()
            ds = DatasetRow(
                session_id=sess.id, name="foo.csv",
                file_path="/data/foo.csv", file_type="csv",
                row_count=5,
                columns_json=json.dumps([{"name": "x", "type": "INTEGER"}]),
            )
            s.add(ds)
            s.commit()
            sess_id, ds_id = sess.id, ds.id

        r = api_client.get(f"/datasets?session_id={sess_id}")
        assert r.status_code == 200
        items = r.json()["data"]
        assert len(items) == 1
        assert items[0]["dataset_id"] == ds_id
        assert items[0]["name"] == "foo.csv"
        assert items[0]["columns"] == [{"name": "x", "type": "INTEGER"}]


# ---------------------------------------------------------------------------
# /chat
# ---------------------------------------------------------------------------

class TestChat:
    def test_blank_question_returns_400(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.commit()
            sess_id = sess.id

        r = api_client.get(f"/chat?session_id={sess_id}&q=   ")
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "INVALID_QUESTION"

    def test_session_not_found_returns_404(self, api_client):
        r = api_client.get("/chat?session_id=nonexistent&q=hello")
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "SESSION_NOT_FOUND"

    def test_valid_chat_streams_sse(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.commit()
            sess_id = sess.id

        def mock_runner(session_id, question):
            yield "event: status\ndata: {\"node\": \"classify_intent\", \"message\": \"Analysing...\"}\n\n"
            yield "event: done\ndata: {\"message_id\": \"msg-1\", \"status\": \"completed\"}\n\n"

        with patch("graph.runner.run_analyst", mock_runner):
            r = api_client.get(
                f"/chat?session_id={sess_id}&q=What+is+the+total+revenue",
                headers={"Accept": "text/event-stream"},
            )

        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        body = r.text
        assert "event: status" in body
        assert "event: done" in body


# ---------------------------------------------------------------------------
# /audit
# ---------------------------------------------------------------------------

class TestAuditLog:
    def test_session_not_found_returns_404(self, api_client):
        r = api_client.get("/audit?session_id=nonexistent")
        assert r.status_code == 404

    def test_empty_audit_log(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.commit()
            sess_id = sess.id

        r = api_client.get(f"/audit?session_id={sess_id}")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] == 0
        assert data["entries"] == []

    def test_lists_audit_entries(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.flush()
            msg = MessageRow(session_id=sess.id, role="assistant", content="{}", status="completed")
            s.add(msg)
            s.flush()
            ql = QueryLogRow(
                session_id=sess.id,
                message_id=msg.id,
                dataset_name="sales.csv",
                sql="SELECT 1",
                row_count=1,
                latency_ms=10,
            )
            s.add(ql)
            s.commit()
            sess_id = sess.id

        r = api_client.get(f"/audit?session_id={sess_id}")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] == 1
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["dataset_name"] == "sales.csv"
        assert entry["sql"] == "SELECT 1"
        assert entry["row_count"] == 1
        assert entry["latency_ms"] == 10
        assert "query_log_id" in entry
        assert "created_at" in entry

    def test_pagination_limit_offset(self, api_client, _isolated_db):
        with Session(_isolated_db) as s:
            sess = SessionRow(name="Session 1")
            s.add(sess)
            s.flush()
            msg = MessageRow(session_id=sess.id, role="assistant", content="{}", status="completed")
            s.add(msg)
            s.flush()
            for i in range(5):
                s.add(QueryLogRow(
                    session_id=sess.id, message_id=msg.id,
                    dataset_name="d.csv", sql=f"SELECT {i}",
                    row_count=i,
                ))
            s.commit()
            sess_id = sess.id

        r = api_client.get(f"/audit?session_id={sess_id}&limit=2&offset=0")
        data = r.json()["data"]
        assert data["total"] == 5
        assert len(data["entries"]) == 2

        r2 = api_client.get(f"/audit?session_id={sess_id}&limit=2&offset=2")
        data2 = r2.json()["data"]
        assert data2["total"] == 5
        assert len(data2["entries"]) == 2


# ---------------------------------------------------------------------------
# /runs (stub)
# ---------------------------------------------------------------------------

class TestRunsStub:
    def test_post_runs_returns_501(self, api_client):
        r = api_client.post("/runs", json={"input_text": "hello"})
        assert r.status_code == 501

    def test_get_run_returns_501(self, api_client):
        r = api_client.get("/runs/some-id")
        assert r.status_code == 501
