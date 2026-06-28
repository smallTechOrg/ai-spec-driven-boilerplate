"""data analyst schema

Extends the skeleton's `runs` table in place (input_text -> question,
output_text -> result_summary_json, plus plan/SQL/token/cost columns) and adds
the dataset library, conversation messages, and workspace sessions.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Extend runs IN PLACE (do not create a parallel table) ---
    with op.batch_alter_table("runs") as batch:
        batch.alter_column("input_text", new_column_name="question",
                           existing_type=sa.Text(), nullable=True)
        batch.alter_column("output_text", new_column_name="result_summary_json",
                           existing_type=sa.Text(), nullable=True)
        batch.add_column(sa.Column("dataset_id", sa.Text(), nullable=True))
        batch.add_column(sa.Column("plan_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("generated_sql", sa.Text(), nullable=True))
        batch.add_column(sa.Column("prompt_tokens", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("completion_tokens", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("est_usd", sa.Float(), nullable=True))

    # --- Dataset library ---
    op.create_table(
        "datasets",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("sheet_name", sa.Text(), nullable=True),
        sa.Column("duckdb_table", sa.Text(), nullable=False),
        sa.Column("profile_json", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Conversation history ---
    op.create_table(
        "messages",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("dataset_id", sa.Text(), nullable=True),
        sa.Column("run_id", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Workspace sessions (modelled now, surfaced Phase 2) ---
    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("active_dataset_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("messages")
    op.drop_table("datasets")
    with op.batch_alter_table("runs") as batch:
        batch.drop_column("est_usd")
        batch.drop_column("completion_tokens")
        batch.drop_column("prompt_tokens")
        batch.drop_column("generated_sql")
        batch.drop_column("plan_json")
        batch.drop_column("dataset_id")
        batch.alter_column("result_summary_json", new_column_name="output_text",
                           existing_type=sa.Text(), nullable=True)
        batch.alter_column("question", new_column_name="input_text",
                           existing_type=sa.Text(), nullable=True)
