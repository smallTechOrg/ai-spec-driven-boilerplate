from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from db.session import init_db
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Data Analyst Agent", version="0.1.0", lifespan=_lifespan)
    from api import health, runs, sessions
    app.include_router(health.router)
    app.include_router(runs.router)
    app.include_router(sessions.router)

    frontend_out = Path(__file__).resolve().parent.parent.parent / "frontend" / "out"
    if frontend_out.exists():
        app.mount("/app", StaticFiles(directory=str(frontend_out), html=True), name="frontend")

    return app


app = create_app()
