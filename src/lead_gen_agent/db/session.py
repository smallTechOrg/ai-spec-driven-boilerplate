from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        from lead_gen_agent.config.settings import get_settings
        _engine = create_engine(get_settings().database_url, echo=False, future=True)
    return _engine


def _get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=_get_engine(), autoflush=False, autocommit=False
        )
    return _SessionLocal


def get_session() -> Generator[Session, None, None]:
    with _get_session_factory()() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@contextmanager
def create_db_session() -> Generator[Session, None, None]:
    with _get_session_factory()() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def init_db() -> None:
    from sqlalchemy import inspect
    from lead_gen_agent.db.models import Base
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
    # Schema sanity check: catch DBs left over from an older, incompatible build
    # whose alembic_version sits on an unknown revision and silently no-ops upgrades.
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            raise RuntimeError(
                f"table '{table.name}' missing from database — run `uv run alembic upgrade head`."
            )
        actual = {c["name"] for c in inspector.get_columns(table.name)}
        expected = {c.name for c in table.columns}
        missing = expected - actual
        if missing:
            raise RuntimeError(
                f"table '{table.name}' is missing columns {sorted(missing)} — this DB "
                "was created by an incompatible prior build. Recreate it: "
                f"`dropdb <db> && createdb <db> && uv run alembic upgrade head`."
            )
