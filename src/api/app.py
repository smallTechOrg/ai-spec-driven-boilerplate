from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.health import router as health_router
from src.api.ui import router as ui_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Analyst",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(ui_router)
    # Register additional routers here
    return app


app = create_app()
