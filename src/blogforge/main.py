from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from blogforge.config import settings
from blogforge.db.session import init_db

DASHBOARD = Path(__file__).parent / "dashboard" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="BlogForge", lifespan=lifespan)

    from blogforge.api.blog import router as blog_router
    from blogforge.api.writers import router as writers_router
    from blogforge.api.runs import router as runs_router
    from blogforge.api.posts import router as posts_router

    app.include_router(blog_router)
    app.include_router(writers_router)
    app.include_router(runs_router)
    app.include_router(posts_router)

    # Serve cover images
    images_dir = settings.images_path()
    app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")

    @app.get("/", include_in_schema=False)
    async def dashboard():
        return FileResponse(DASHBOARD)

    return app


app = create_app()
