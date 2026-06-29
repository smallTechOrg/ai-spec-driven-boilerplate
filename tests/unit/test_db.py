"""DB layer tests — no LLM key required."""
from sqlalchemy.orm import Session
from db.models import SessionRow, UploadedFileRow, MessageRow
import db.session as session_module


def test_session_row_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        row = SessionRow()
        s.add(row)
        s.commit()
        sid = row.id

    with Session(_isolated_db) as s:
        fetched = s.get(SessionRow, sid)
        assert fetched is not None
        assert fetched.id == sid
        assert fetched.created_at is not None
        assert fetched.expires_at is not None


def test_uploaded_file_row_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        sess = SessionRow()
        s.add(sess)
        s.commit()
        sid = sess.id

    with Session(_isolated_db) as s:
        f = UploadedFileRow(
            session_id=sid,
            filename="test.csv",
            temp_path="/tmp/test.csv",
            profile_json='{"row_count": 10}',
        )
        s.add(f)
        s.commit()
        fid = f.id

    with Session(_isolated_db) as s:
        fetched = s.get(UploadedFileRow, fid)
        assert fetched is not None
        assert fetched.filename == "test.csv"
        assert fetched.session_id == sid


def test_message_row_roundtrip(_isolated_db):
    with Session(_isolated_db) as s:
        sess = SessionRow()
        s.add(sess)
        s.commit()
        sid = sess.id

    with Session(_isolated_db) as s:
        msg = MessageRow(session_id=sid, role="user", content="hello")
        s.add(msg)
        s.commit()
        mid = msg.id

    with Session(_isolated_db) as s:
        fetched = s.get(MessageRow, mid)
        assert fetched is not None
        assert fetched.role == "user"
        assert fetched.content == "hello"
        assert fetched.chart_json is None
