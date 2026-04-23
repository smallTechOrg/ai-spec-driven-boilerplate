from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from food_tracker.api.food import router
from food_tracker.config.settings import get_settings
from food_tracker.llm.providers.factory import create_provider
from food_tracker.observability.events import configure_logging

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    app.state.provider = create_provider(settings)
    app.state.settings = settings
    app.state.templates = templates
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Food Tracker", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app
