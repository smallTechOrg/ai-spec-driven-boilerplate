import os

os.environ["APP_DATABASE_URL"] = "sqlite+aiosqlite:///./test_agent.db"   # set BEFORE importing agent.db

import pytest_asyncio

from agent.db import Base, engine
from agent import domain  # noqa: F401 — register the Ticket table on Base.metadata before create_all


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    # NOTE: tests/e2e/conftest.py shadows this with a sync no-op — the Playwright tier drives the live HTTP
    # server (its own DB) and its sync `page` fixture runs its own event loop, which collides with a
    # co-resident async autouse fixture at Runner teardown. The override keeps the e2e tier loop-clean.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
