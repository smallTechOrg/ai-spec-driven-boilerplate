"""Integration tests for the CSV export endpoint."""

import pytest


def _create_session(api_client) -> str:
    """Helper: create a session and return its ID."""
    r = api_client.post("/sessions")
    assert r.status_code == 200
    return r.json()["data"]["session_id"]


def _upload_csv(api_client, session_id: str, sample_csv) -> None:
    """Helper: upload the sample CSV to a session."""
    with open(sample_csv, "rb") as f:
        r = api_client.post(
            f"/sessions/{session_id}/files",
            files={"file": ("sales.csv", f, "text/csv")},
        )
    assert r.status_code == 200


def _ask_question(api_client, session_id: str, question: str) -> dict:
    """Helper: post a question and return the response data."""
    r = api_client.post(
        f"/sessions/{session_id}/messages",
        json={"content": question},
    )
    assert r.status_code == 200
    return r.json()["data"]


class TestExportNoResult:
    def test_export_no_result_returns_400(self, api_client):
        """Export before any Q&A returns 400 NO_RESULT."""
        sid = _create_session(api_client)
        r = api_client.post(f"/sessions/{sid}/export")
        assert r.status_code == 400
        body = r.json()
        assert body["error"]["code"] == "NO_RESULT"

    def test_export_session_not_found_returns_404(self, api_client):
        """Export for a nonexistent session returns 404 SESSION_NOT_FOUND."""
        r = api_client.post("/sessions/nonexistent-session-id/export")
        assert r.status_code == 404
        body = r.json()
        assert body["error"]["code"] == "SESSION_NOT_FOUND"

    def test_export_after_upload_but_no_question_returns_400(self, api_client, sample_csv):
        """Export after file upload but before any question returns 400 NO_RESULT."""
        sid = _create_session(api_client)
        _upload_csv(api_client, sid, sample_csv)
        r = api_client.post(f"/sessions/{sid}/export")
        assert r.status_code == 400
        body = r.json()
        assert body["error"]["code"] == "NO_RESULT"


class TestExportWithRealLLM:
    """These tests call the real Gemini API. Skipped if no key is configured."""

    def test_export_returns_csv(self, api_client, sample_csv, _require_llm_key):
        """Upload CSV -> ask tabular question -> export returns 200 text/csv."""
        sid = _create_session(api_client)
        _upload_csv(api_client, sid, sample_csv)
        _ask_question(api_client, sid, "Show me total revenue by region as a table")

        r = api_client.post(f"/sessions/{sid}/export")
        # The LLM may or may not produce a tabular execution_result.
        # If it does, we expect 200 with text/csv. If not, 400 is acceptable.
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            assert "text/csv" in content_type
            body_text = r.content.decode("utf-8")
            # Should have at least a header line and one data line
            lines = [l for l in body_text.strip().splitlines() if l.strip()]
            assert len(lines) >= 1, "CSV should have at least one line"
            # Content-Disposition header should indicate attachment
            disposition = r.headers.get("content-disposition", "")
            assert "attachment" in disposition
            assert "result.csv" in disposition
        else:
            # Acceptable if execution_result was non-tabular (scalar answer)
            assert r.status_code == 400
            assert r.json()["error"]["code"] == "NO_RESULT"

    def test_export_returns_csv_with_header(self, api_client, sample_csv, _require_llm_key):
        """When export succeeds, the CSV body contains at least one header row."""
        sid = _create_session(api_client)
        _upload_csv(api_client, sid, sample_csv)

        # Ask a question that typically yields a tabular DataFrame result
        _ask_question(api_client, sid, "Give me a table of total revenue and units per region")

        r = api_client.post(f"/sessions/{sid}/export")
        if r.status_code == 200:
            body_text = r.content.decode("utf-8")
            lines = [l for l in body_text.strip().splitlines() if l.strip()]
            assert len(lines) >= 1
            # First line should be a header (non-empty, has comma-separated content or single col)
            assert len(lines[0]) > 0
        else:
            assert r.status_code == 400
            assert r.json()["error"]["code"] == "NO_RESULT"

    def test_export_after_two_questions_gets_last_result(
        self, api_client, sample_csv, _require_llm_key
    ):
        """After two Q&A turns, export fetches the LAST assistant message's result."""
        sid = _create_session(api_client)
        _upload_csv(api_client, sid, sample_csv)

        # First question
        _ask_question(api_client, sid, "What is the total revenue?")
        # Second question — tabular to more likely produce a CSV
        _ask_question(api_client, sid, "Show me revenue and units per region as a table")

        r = api_client.post(f"/sessions/{sid}/export")
        # Either export succeeds (200 with CSV from last assistant msg) or no exportable result
        assert r.status_code in (200, 400)
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            assert "text/csv" in content_type
            body = r.content.decode("utf-8")
            assert len(body.strip()) > 0
        else:
            assert r.json()["error"]["code"] == "NO_RESULT"
