"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sourcing_agent.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up DB tables on startup (idempotent — alembic is the canonical migration path)
    from sourcing_agent.db.session import init_db

    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sourcing Agent",
        description="AI-powered construction materials sourcing",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app
