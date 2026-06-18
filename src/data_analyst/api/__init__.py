from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_FRONTEND_DIST = Path(__file__).parent.parent.parent.parent / "src" / "frontend" / "dist"


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

    if _FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

        @app.get("/", include_in_schema=False)
        @app.get("/{catchall:path}", include_in_schema=False)
        async def spa(catchall: str = ""):
            index = _FRONTEND_DIST / "index.html"
            return FileResponse(str(index))

    return app


app = create_app()
