# Pattern: Persistence (Layer — the data spine)

Every run, message, and span lands here. **Generate fresh at build time**, pinning the *current*
`sqlalchemy`, `aiosqlite`, and (for prod) `asyncpg` — verify latest before pinning, a guessed version 404s.
The code below is proven working; use it verbatim.

## The one rule: SQLite local → Postgres prod, same code, swap only the URL
Async SQLAlchemy 2.0 abstracts the backend. You change a **driver/URL**, never a query.

| Rung | `APP_DATABASE_URL` | Driver | When |
|------|--------------------|--------|------|
| **Local-first** | `sqlite+aiosqlite:///./agent.db` | `aiosqlite` | dev, the demo gate, tests |
| **Prod** | `postgresql+asyncpg://user:pw@host/db` | `asyncpg` | `/deploy`, before any deploy gate |

**NEVER `psycopg2`** (sync) — it blocks the event loop and every recipe in this repo assumes async I/O.
Postgres uses `asyncpg`, full stop. The deploy gate runs the *same tests* against the Postgres rung
(`workflows/gates.md`) — that's the whole point of one code path.

## Code — `agent/db.py` (proven, verbatim)
```python
import datetime as dt
import uuid
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from .config import get_settings


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"
    id:         Mapped[str]  = mapped_column(String, primary_key=True, default=_uuid)
    goal:       Mapped[str]  = mapped_column(Text)
    status:     Mapped[str]  = mapped_column(String, default="running")   # running|completed|error
    answer:     Mapped[str | None] = mapped_column(Text, nullable=True)
    iterations: Mapped[int]  = mapped_column(Integer, default=0)
    input_tokens:  Mapped[int]   = mapped_column(Integer, default=0)      # summed from this run's LLM spans
    output_tokens: Mapped[int]   = mapped_column(Integer, default=0)
    cost_usd:      Mapped[float] = mapped_column(Float, default=0.0)       # tokens × per-1M price (config.py)
    thread_id:     Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # multi-turn session
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Message(Base):
    __tablename__ = "messages"
    id:         Mapped[str]  = mapped_column(String, primary_key=True, default=_uuid)
    run_id:     Mapped[str]  = mapped_column(ForeignKey("runs.id"), index=True)
    role:       Mapped[str]  = mapped_column(String)                      # system|human|ai|tool
    content:    Mapped[str]  = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Span(Base):
    __tablename__ = "spans"
    id:          Mapped[str]  = mapped_column(String, primary_key=True, default=_uuid)
    run_id:      Mapped[str]  = mapped_column(ForeignKey("runs.id"), index=True)
    name:        Mapped[str]  = mapped_column(String)                     # OTel GenAI: invoke_agent|chat <model>|execute_tool.<name>
    kind:        Mapped[str]  = mapped_column(String, default="INTERNAL") # INTERNAL|LLM|TOOL
    attributes:  Mapped[dict] = mapped_column(JSON, default=dict)
    start_ms:    Mapped[float] = mapped_column(Float)
    end_ms:      Mapped[float] = mapped_column(Float)
    duration_ms: Mapped[float] = mapped_column(Float)
    created_at:  Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


engine = create_async_engine(get_settings().database_url)
_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


def get_sessionmaker() -> async_sessionmaker:
    """The one session accessor. Callers do: `async with get_sessionmaker()() as s: ...; await s.commit()`."""
    return _sessionmaker


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

`expire_on_commit=False` so objects stay usable after `commit()` (you read `.answer` post-write without a
reload). `get_sessionmaker()` returns the `async_sessionmaker`; every recipe opens a session with
`async with get_sessionmaker()() as s:` and commits explicitly. `init_db()` is wired into the FastAPI
lifespan (`agent/server.py`) so tables exist on boot. `db.py` exports `get_sessionmaker` and `init_db`.

## The three core tables — the agent's flight recorder
- **`runs`** — one row per `POST /runs`. The unit of work: goal in, answer + status + iteration count out.
- **`messages`** — the full transcript (system/human/ai/tool), keyed to a run. Persisted by `agent/runner.py`
  after the graph finishes.
- **`spans`** — one row per LLM call and tool execution, OTel-GenAI-shaped, written by the `span()` context
  manager (`patterns/observability-and-evals.md`). The built-in `/traces` viewer reads straight from this table.

These three are non-negotiable: they *are* observability + evals. Don't skip `spans` to "add it later" —
the demo gate requires visible traces.

**Cost is a first-class column, not an afterthought.** Every run consumes tokens and money, so `runs` carries
`input_tokens` / `output_tokens` / `cost_usd` from Phase 1 — sum the run's `LLM` spans' `usage_metadata`,
price via per-1M rates in `agent/config.py`. Wiring this in later means a migration *and* a UI retrofit; from
the start it's free. For **multi-turn** products add a `threads` (session) table keyed by `thread_id` that
accumulates per-session token + cost totals and the active resource id — that row is what the UI's
always-visible session header reads (`patterns/interface.md`).

## Adding domain entities — extend, don't fork
Your capability's nouns (tickets, invoices, documents, …) are new models on the **same `Base`**. Same engine,
same session, same SQLite→Postgres ladder — `init_db()` creates them automatically.

```python
# agent/domain.py — domain entities live alongside the core tables
import datetime as dt
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, _now, _uuid   # reuse the same declarative Base + helpers — do NOT define a second Base

class Ticket(Base):                 # example: a support agent's domain noun
    __tablename__ = "tickets"
    id:         Mapped[str]  = mapped_column(String, primary_key=True, default=_uuid)
    run_id:     Mapped[str]  = mapped_column(ForeignKey("runs.id"), index=True)  # tie domain rows to the run
    subject:    Mapped[str]  = mapped_column(String)
    body:       Mapped[str]  = mapped_column(Text)
    status:     Mapped[str]  = mapped_column(String, default="open")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

Rules: **one `Base`** (a second one means tables your `init_db()` never creates); reference `runs.id` so
domain data joins back to the run that produced it; index your foreign keys. Tools that write domain rows are
plain in-process `@tool`s using the same `get_sessionmaker()` (`patterns/tools-and-mcp.md`).

### Writing rows — the session pattern
```python
from .db import get_sessionmaker
from .domain import Ticket

async def open_ticket(run_id: str, subject: str, body: str) -> str:
    async with get_sessionmaker()() as session:
        t = Ticket(run_id=run_id, subject=subject, body=body)
        session.add(t)
        await session.commit()      # async all the way down — never a sync driver
        return t.id
```

Beyond `commit()`: stays async end-to-end, so it never blocks the loop. For long writes, hand off with
`asyncio.create_task` and return the turn immediately (the async-write rule in `patterns/memory.md`).

## Migrations — when the schema outgrows `create_all`
`init_db()`'s `create_all` makes *new* tables but never *alters* existing ones. The moment a deployed
Postgres DB has data you can't drop, add **Alembic** (pin current): `alembic init`, point `sqlalchemy.url` at
`APP_DATABASE_URL`, autogenerate against the same `Base.metadata`. Local SQLite dev keeps using `create_all`;
prod runs migrations. This earns its place at `/deploy`, not before.

## Tests use the SAME driver as prod (conftest, proven pattern)
Tests must not invent a special path — they exercise the real async engine, just against a throwaway DB. Set
`APP_DATABASE_URL` before importing `agent.db` (the engine is built at import time), and create/drop tables
per test for isolation.

```python
# tests/conftest.py
import os
os.environ["APP_DATABASE_URL"] = "sqlite+aiosqlite:///./test_agent.db"   # set BEFORE importing agent.db
import pytest_asyncio
from agent.db import Base, engine

@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```
The local demo gate runs these on SQLite. The **deploy gate runs the identical suite with
`APP_DATABASE_URL` pointed at a real Postgres+`asyncpg`** — same models, same code path, proving the URL
swap before any deploy. A green SQLite suite is necessary, not sufficient. → `workflows/gates.md`.

## Spec wiring
`spec/tech-stack.md` sets the DB rung (SQLite local default → Postgres deploy target) and declares domain
entities the capability needs. `spec/capabilities/*.md` EARS criteria name the rows a run must produce — the
outcome eval reads them back from these tables to grade the run.
