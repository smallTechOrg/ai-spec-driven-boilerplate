"""add supplier dossier columns

Revision ID: bb6585b0d552
Revises: 4c54f7d953bf
Create Date: 2026-04-25 13:00:46.355453

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bb6585b0d552"
down_revision: Union[str, None] = "4c54f7d953bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("google_rating", sa.Float(), nullable=True))
    op.add_column("suppliers", sa.Column("google_review_count", sa.Integer(), nullable=True))
    op.add_column("suppliers", sa.Column("feedback_summary", sa.Text(), nullable=True))
    op.add_column("suppliers", sa.Column("delivery_reliability", sa.Text(), nullable=True))
    op.add_column("suppliers", sa.Column("years_in_business", sa.Integer(), nullable=True))
    op.add_column("suppliers", sa.Column("solvency_signal", sa.Text(), nullable=True))
    op.add_column("suppliers", sa.Column("gst_registered", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("suppliers", "gst_registered")
    op.drop_column("suppliers", "solvency_signal")
    op.drop_column("suppliers", "years_in_business")
    op.drop_column("suppliers", "delivery_reliability")
    op.drop_column("suppliers", "feedback_summary")
    op.drop_column("suppliers", "google_review_count")
    op.drop_column("suppliers", "google_rating")
