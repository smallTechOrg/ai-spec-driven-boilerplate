"""add last_result_csv to messages

Revision ID: a1b2c3d4e5f6
Revises: 4e5e9d30239c
Create Date: 2026-06-29 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4e5e9d30239c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('messages', sa.Column('last_result_csv', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'last_result_csv')
