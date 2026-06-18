"""Shared test fixtures — real SQLite (same driver as production), settings reset."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import datachat.config.settings as settings_module
from datachat.db.models import Base

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///./datachat_test.db"
)


@pytest.fixture(autouse=True)
def _reset_settings_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings singleton must be resettable (project-layout rule 9)."""
    monkeypatch.setattr(settings_module, "_settings", None)


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
