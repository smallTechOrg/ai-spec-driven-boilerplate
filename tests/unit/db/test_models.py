"""Unit tests for the Phase-1 SQLAlchemy models."""
from src.db.models import Base, Conversation, Dataset, Turn


def _columns(model) -> set[str]:
    return set(model.__table__.columns.keys())


def test_dataset_columns():
    assert Dataset.__tablename__ == "datasets"
    assert _columns(Dataset) == {
        "id",
        "name",
        "file_path",
        "source_kind",
        "row_count",
        "column_count",
        "profile",
        "sample_rows",
        "derived_from",
        "created_at",
    }


def test_conversation_columns():
    assert Conversation.__tablename__ == "conversations"
    assert _columns(Conversation) == {
        "id",
        "dataset_id",
        "title",
        "created_at",
    }


def test_turn_columns():
    assert Turn.__tablename__ == "turns"
    assert _columns(Turn) == {
        "id",
        "conversation_id",
        "question",
        "plan",
        "code",
        "result_table",
        "answer",
        "chart_spec",
        "follow_ups",
        "prompt_tokens",
        "completion_tokens",
        "estimated_cost_usd",
        "status",
        "error_message",
        "created_at",
    }


def test_foreign_keys_registered():
    conv_fks = {fk.target_fullname for fk in Conversation.__table__.foreign_keys}
    turn_fks = {fk.target_fullname for fk in Turn.__table__.foreign_keys}
    assert "datasets.id" in conv_fks
    assert "conversations.id" in turn_fks


def test_models_share_base_metadata():
    for tbl in ("datasets", "conversations", "turns"):
        assert tbl in Base.metadata.tables
