import uuid

import duckdb

from src.db.connection import get_db


def ensure_session(conn: duckdb.DuckDBPyConnection, session_id: str) -> str:
    """Create session row if it doesn't exist. Returns session_id."""
    existing = conn.execute(
        "SELECT id FROM sessions WHERE id = ?", [session_id]
    ).fetchone()
    if not existing:
        conn.execute("INSERT INTO sessions (id) VALUES (?)", [session_id])
    return session_id


def save_message(
    conn: duckdb.DuckDBPyConnection,
    session_id: str,
    role: str,
    content: str,
) -> None:
    conn.execute(
        "INSERT INTO messages (id, session_id, role, content) VALUES (?, ?, ?, ?)",
        [str(uuid.uuid4()), session_id, role, content],
    )


def load_history(
    conn: duckdb.DuckDBPyConnection,
    session_id: str,
    limit: int = 10,
) -> list[dict]:
    """Return recent messages for a session, oldest first."""
    rows = conn.execute(
        """SELECT role, content FROM messages
           WHERE session_id = ?
           ORDER BY created_at ASC
           LIMIT ?""",
        [session_id, limit],
    ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]
