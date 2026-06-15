from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from data_analysis_agent.db.session import init_db
    from data_analysis_agent.config.settings import get_settings
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Data Analysis Agent",
        version="0.1.0",
        lifespan=_lifespan,
    )

    from data_analysis_agent.api import health, datasets
    app.include_router(health.router)
    app.include_router(datasets.router)

    return app


app = create_app()
