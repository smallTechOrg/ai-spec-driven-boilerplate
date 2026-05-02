from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from up_police_ai.config.settings import get_settings
from up_police_ai.db.models import Base

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url)
    return _engine


def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=_get_engine(), autoflush=False, autocommit=False
        )
    return _SessionLocal


def get_session() -> Generator[Session, None, None]:
    SessionLocal = _get_session_local()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_db_session() -> Session:
    SessionLocal = _get_session_local()
    return SessionLocal()


def init_db() -> None:
    engine = _get_engine()
    Base.metadata.create_all(engine)
