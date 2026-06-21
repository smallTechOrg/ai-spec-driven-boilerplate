"""SQLite spine — async engine, session factory, schema bootstrap.

The engine is created in ``init_db`` (not at import time) so importing this module
never touches the filesystem or pins a stale settings value.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings
from src.db.base import Base
from src.db.duck import init_event_store

_engine = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    global _engine, AsyncSessionLocal
    settings = get_settings()
    _engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

    # Bootstrap the relational schema via create_all (no migrations shipped).
    # Importing the models module registers every table on Base.metadata first.
    import src.db.models  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Bootstrap the DuckDB columnar event-store seam (the storage layer that makes
    # this recipe differ from python-fastapi-sqlite).
    init_event_store()


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
