from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings
from src.db.base import Base

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


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
