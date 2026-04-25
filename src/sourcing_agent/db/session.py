"""Database engine and session management."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        from sourcing_agent.config.settings import get_settings

        _engine = create_engine(get_settings().database_url, echo=False)
    return _engine


def _get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    factory = _get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables. Used in tests; production uses alembic migrations."""
    from sourcing_agent.db.models import Base

    Base.metadata.create_all(bind=_get_engine())


def reset_engine() -> None:
    """Reset cached engine and session factory — used in tests only."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
