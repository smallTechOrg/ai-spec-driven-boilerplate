# Data

## Storage Overview

SQLite database at `data/agent.db` (relative to repo root). Three tables: sessions, uploaded_files, messages. All data is session-scoped and ephemeral. On session deletion (or server restart), all rows and temp files for the session are removed.

---

## Sessions Table

```python
class SessionRow(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_now)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    # expires_at = created_at + 1 hour; used for cleanup on server startup
```

---

## Uploaded Files Table

```python
class UploadedFileRow(Base):
    __tablename__ = "uploaded_files"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(Text, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)  # original filename e.g. "sales.csv"
    temp_path: Mapped[str] = mapped_column(Text, nullable=False)  # absolute path to temp file
    profile_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON blob of profile result
    uploaded_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_now)
```

---

## Messages Table

```python
class MessageRow(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(Text, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chart_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Plotly JSON string or NULL
    quality_report: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON blob from inspect_quality or NULL (Phase 4)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_now)
```

---

## Temp File Storage

CSV files stored at `{tempfile.gettempdir()}/agent_sessions/{session_id}/{original_filename}`.

On session deletion: remove entire `{TEMP_DIR}/agent_sessions/{session_id}/` directory.

On server startup: scan `{TEMP_DIR}/agent_sessions/` for directories whose session_id does not exist in the sessions table (or whose expires_at has passed) and delete them.

---

## Privacy

`profile_json` in `uploaded_files` contains ONLY statistical metadata — no raw row values.

`chart_json` in `messages` contains aggregated Plotly trace data (e.g. bar chart heights) — not raw rows.

The LLM (Gemini) receives only: column names, dtypes, statistical summaries (min/max/mean/std/percentiles, top-5 value_counts, null counts). Never receives raw row values.

---

## Migrations

Managed by Alembic. `alembic/env.py` sets `target_metadata = Base.metadata`. The existing `RunRow` model is replaced by `SessionRow`, `UploadedFileRow`, and `MessageRow`.

Initial migration: `uv run alembic revision --autogenerate -m "initial"`
Apply: `uv run alembic upgrade head`
Verify: `uv run alembic current` (must show a revision hash, not blank)

Phase 4 adds `quality_report` column to `messages`. Migration: `uv run alembic revision --autogenerate -m "add_quality_report_to_messages"` then `uv run alembic upgrade head`. The column is nullable so existing rows are unaffected.
