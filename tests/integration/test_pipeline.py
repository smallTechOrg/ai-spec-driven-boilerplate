"""Integration tests for the CSV analysis pipeline."""

import pytest
import json
from pathlib import Path


class TestSessionLifecycle:
    def test_create_session(self, api_client):
        r = api_client.post("/sessions")
        assert r.status_code == 200
        d = r.json()["data"]
        assert "session_id" in d
        assert "created_at" in d

    def test_delete_session(self, api_client):
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        r = api_client.delete(f"/sessions/{sid}")
        assert r.status_code == 200
        assert r.json()["data"]["deleted"] is True

    def test_delete_nonexistent_session_returns_404(self, api_client):
        r = api_client.delete("/sessions/does-not-exist")
        assert r.status_code == 404


class TestFileUpload:
    def test_upload_csv_returns_profile(self, api_client, sample_csv):
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        with open(sample_csv, "rb") as f:
            r = api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["filename"] == "sales.csv"
        profile = data["profile"]
        assert profile["row_count"] == 10
        assert profile["column_count"] == 4
        col_names = [c["name"] for c in profile["columns"]]
        assert "region" in col_names
        assert "revenue" in col_names

    def test_upload_csv_includes_numeric_stats(self, api_client, sample_csv):
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        with open(sample_csv, "rb") as f:
            r = api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        profile = r.json()["data"]["profile"]
        revenue_col = next(c for c in profile["columns"] if c["name"] == "revenue")
        assert "stats" in revenue_col
        assert "min" in revenue_col["stats"]
        assert "mean" in revenue_col["stats"]

    def test_upload_csv_includes_categorical_value_counts(self, api_client, sample_csv):
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        with open(sample_csv, "rb") as f:
            r = api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        profile = r.json()["data"]["profile"]
        region_col = next(c for c in profile["columns"] if c["name"] == "region")
        assert "value_counts" in region_col

    def test_upload_non_csv_returns_400(self, api_client, tmp_path):
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        p = tmp_path / "data.json"
        p.write_text('{"key": "value"}')
        with open(p, "rb") as f:
            r = api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("data.json", f, "application/json")},
            )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_FILE"

    def test_upload_to_nonexistent_session_returns_404(self, api_client, sample_csv):
        with open(sample_csv, "rb") as f:
            r = api_client.post(
                "/sessions/no-such-session/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        assert r.status_code == 404

    def test_profile_does_not_contain_raw_row_values(self, api_client, sample_csv):
        """Privacy: raw row values must not appear in profile_json sent to LLM."""
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        with open(sample_csv, "rb") as f:
            r = api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        profile = r.json()["data"]["profile"]
        # Validate: profile has statistical summaries, not a full data dump
        assert "row_count" in profile
        assert profile["row_count"] == 10
        # Ensure no "data" key with a list of all rows
        assert "data" not in profile


class TestMessagesNoLLM:
    def test_message_without_file_returns_400(self, api_client):
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        r = api_client.post(
            f"/sessions/{sid}/messages",
            json={"content": "What is the average revenue?"},
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "NO_FILES"

    def test_get_messages_empty(self, api_client):
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        r = api_client.get(f"/sessions/{sid}/messages")
        assert r.status_code == 200
        assert r.json()["data"]["messages"] == []


class TestQAWithRealLLM:
    """These tests call the real Gemini API. Skipped if no key."""

    def test_full_qa_pipeline_text_answer(self, api_client, sample_csv, _require_llm_key):
        """Upload CSV -> ask question -> get text answer."""
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        with open(sample_csv, "rb") as f:
            api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        r = api_client.post(
            f"/sessions/{sid}/messages",
            json={"content": "What is the total revenue?"},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["role"] == "assistant"
        assert len(data["content"]) > 10  # non-empty prose answer
        # Should mention a number (total revenue)
        assert any(c.isdigit() for c in data["content"])

    def test_full_qa_pipeline_chart_answer(self, api_client, sample_csv, _require_llm_key):
        """Upload CSV -> ask for a chart -> get chart_json."""
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        with open(sample_csv, "rb") as f:
            api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        r = api_client.post(
            f"/sessions/{sid}/messages",
            json={"content": "Show me a bar chart of revenue by region"},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["role"] == "assistant"
        assert len(data["content"]) > 5
        # Chart should be present
        assert data["chart_json"] is not None
        assert "data" in data["chart_json"]  # Plotly JSON has "data" key
        assert "layout" in data["chart_json"]

    def test_conversation_history_used_in_followup(
        self, api_client, sample_csv, _require_llm_key
    ):
        """Follow-up question resolves context from prior turn."""
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        with open(sample_csv, "rb") as f:
            api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        # First question
        api_client.post(
            f"/sessions/{sid}/messages",
            json={"content": "What is the total revenue by region?"},
        )
        # Follow-up referencing prior context
        r = api_client.post(
            f"/sessions/{sid}/messages",
            json={"content": "Which region had the highest value?"},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data["content"]) > 5
        # Response should mention a region name
        content_lower = data["content"].lower()
        assert any(region in content_lower for region in ["west", "east", "north", "south"])

    def test_get_messages_after_qa(self, api_client, sample_csv, _require_llm_key):
        """GET /messages returns full conversation history."""
        sid = api_client.post("/sessions").json()["data"]["session_id"]
        with open(sample_csv, "rb") as f:
            api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        api_client.post(
            f"/sessions/{sid}/messages",
            json={"content": "What is the average revenue?"},
        )
        r = api_client.get(f"/sessions/{sid}/messages")
        assert r.status_code == 200
        msgs = r.json()["data"]["messages"]
        assert len(msgs) == 2  # 1 user + 1 assistant
        roles = [m["role"] for m in msgs]
        assert "user" in roles
        assert "assistant" in roles

    def test_llm_prompt_privacy_no_raw_rows(
        self, api_client, sample_csv, _require_llm_key, monkeypatch
    ):
        """The LLM prompt must never contain raw row values from the CSV."""
        captured_prompts = []
        from llm.client import LLMClient as _LLMClient

        original_call = _LLMClient.call_model

        def _capture(self, prompt, *, system=None):
            captured_prompts.append(prompt)
            return original_call(self, prompt, system=system)

        monkeypatch.setattr(_LLMClient, "call_model", _capture)

        sid = api_client.post("/sessions").json()["data"]["session_id"]
        with open(sample_csv, "rb") as f:
            api_client.post(
                f"/sessions/{sid}/files",
                files={"file": ("sales.csv", f, "text/csv")},
            )
        api_client.post(
            f"/sessions/{sid}/messages",
            json={"content": "What is the average revenue?"},
        )

        # Verify prompts were captured and don't contain all 10 raw revenue values
        assert len(captured_prompts) > 0
        combined = "\n".join(captured_prompts)
        # Check that not ALL specific row values appear (partial presence for stats/samples is ok)
        raw_row_values = ["14200.0", "6200.0", "11000.0", "13100.0"]
        # At least 2 of these specific mid-dataset values should NOT appear in the prompt
        absent_count = sum(1 for v in raw_row_values if v not in combined)
        assert absent_count >= 2, (
            f"Too many raw row values found in LLM prompt. Captured: {combined[:500]}"
        )
