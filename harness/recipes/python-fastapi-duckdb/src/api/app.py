from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import src.db.session as db_session
from src.api.health import router as health_router
from src.api.routes import router as run_router
from src.api.ui import router as ui_router
from src.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Reference through the module so tests can patch init_db to a no-op.
    await db_session.init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="appname",
        version="0.1.0",
        lifespan=lifespan,
    )
    # Single configurable origin list — never mix "*" with explicit origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(ui_router)
    app.include_router(run_router)
    # Register additional routers here
    return app


app = create_app()
