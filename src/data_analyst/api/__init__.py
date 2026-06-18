from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from data_analyst.db.session import init_db
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="DataChat", version="0.1.0", lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from data_analyst.api import health, sessions, chat
    app.include_router(health.router)
    app.include_router(sessions.router, prefix="/api/sessions")
    app.include_router(chat.router, prefix="/api/sessions")

    return app


app = create_app()
