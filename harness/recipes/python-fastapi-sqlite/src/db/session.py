from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings
from src.db.base import Base

# Module-level engine/factory, created lazily by init_db() — NOT at import time.
#
# Footgun: if you build the engine at import time, it binds to whatever
# database_url is set when the module is first imported, before tests get a
# chance to point it at a throwaway DB. tests/conftest.py works around this by
# monkeypatching AsyncSessionLocal after init_db() would have run, and stubbing
# init_db() to a no-op. Keep these module-level and assigned in init_db().
_engine = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    global _engine, AsyncSessionLocal
    settings = get_settings()
    _engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

    # Bootstrap the schema via create_all (no migrations shipped). Importing the
    # models module registers every table on Base.metadata before we create them.
    import src.db.models  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a session bound to the live engine. Used by the example route."""
    assert AsyncSessionLocal is not None, "init_db() must run before get_session()"
    async with AsyncSessionLocal() as session:
        yield session
