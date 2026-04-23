import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from emailtriage.db.models import Base

@pytest.fixture
async def db_session(tmp_path) -> AsyncSession:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
