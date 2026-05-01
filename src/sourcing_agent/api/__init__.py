from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from sourcing_agent.api.routes import router


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from sourcing_agent.db.session import init_db

    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Sourcing Agent", version="0.1.0", lifespan=_lifespan)
    app.include_router(router)
    return app


app = create_app()
