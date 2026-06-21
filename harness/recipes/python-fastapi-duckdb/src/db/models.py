"""ORM models. Import this module before create_all so tables register on Base.

Schema is bootstrapped via ``Base.metadata.create_all`` in ``init_db`` — no
migrations are shipped, and ``create_all`` defines every column (no ALTER-TABLE
hacks). Add Alembic when you need schema evolution.
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    input: Mapped[str]
    result: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
