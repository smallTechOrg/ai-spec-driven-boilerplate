"""profile + followups marker migration

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-29 00:00:00.000000

The Phase 2 columns `datasets.profile_json` and `runs.followups_json` are
already created by migration 0002 (both nullable). This revision is therefore a
no-op marker that advances the head so the Phase 2 schema has an explicit
revision boundary; `alembic upgrade head` reaches 0003 with the columns present.
"""
from typing import Sequence, Union

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: profile_json / followups_json were created in 0002.
    pass


def downgrade() -> None:
    # No-op: nothing was added in this revision.
    pass
