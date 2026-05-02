import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from up_police_ai.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="UP Police AI Workshop",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="uppolice_session",
    )

    # Static files
    static_dir = pathlib.Path(__file__).parent.parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include routers
    from up_police_ai.api.health import router as health_router
    from up_police_ai.api.officers import router as officers_router
    from up_police_ai.api.assessment import router as assessment_router
    from up_police_ai.api.plan import router as plan_router

    app.include_router(health_router)
    app.include_router(officers_router)
    app.include_router(assessment_router)
    app.include_router(plan_router)

    return app
