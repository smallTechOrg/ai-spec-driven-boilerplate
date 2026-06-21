import os

os.environ["ANALYST_LLM_PROVIDER"] = "stub"

import duckdb
import pytest

from src.db.schema import create_tables
from src.sessions.manager import ensure_session, load_history, save_message


@pytest.fixture
def db():
    conn = duckdb.connect(":memory:")
    create_tables(conn)
    yield conn
    conn.close()


def test_ensure_session_creates_row(db):
    sid = "test-session-1"
    ensure_session(db, sid)
    row = db.execute("SELECT id FROM sessions WHERE id = ?", [sid]).fetchone()
    assert row is not None


def test_ensure_session_idempotent(db):
    """Calling ensure_session twice does not raise."""
    sid = "test-session-2"
    ensure_session(db, sid)
    ensure_session(db, sid)  # second call must not fail (UNIQUE constraint)
    count = db.execute(
        "SELECT COUNT(*) FROM sessions WHERE id = ?", [sid]
    ).fetchone()[0]
    assert count == 1


def test_save_and_load_messages(db):
    sid = "test-session-3"
    ensure_session(db, sid)
    save_message(db, sid, "user", "show top 10 rows")
    save_message(
        db, sid, "assistant", "| product | revenue |\n|---|\n| widget | 100 |"
    )
    history = load_history(db, sid)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "show top 10 rows"
    assert history[1]["role"] == "assistant"


def test_load_history_respects_limit(db):
    sid = "test-session-4"
    ensure_session(db, sid)
    for i in range(15):
        save_message(db, sid, "user", f"question {i}")
    history = load_history(db, sid, limit=5)
    assert len(history) == 5


def test_load_history_empty_session(db):
    sid = "test-session-5"
    ensure_session(db, sid)
    history = load_history(db, sid)
    assert history == []


def test_history_oldest_first(db):
    sid = "test-session-6"
    ensure_session(db, sid)
    save_message(db, sid, "user", "first question")
    save_message(db, sid, "user", "second question")
    history = load_history(db, sid)
    assert history[0]["content"] == "first question"
    assert history[1]["content"] == "second question"
