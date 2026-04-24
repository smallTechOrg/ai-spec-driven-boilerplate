from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from lead_gen_agent.db.session import init_db
    init_db()
    yield


def create_app() -> FastAPI:
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path
    from lead_gen_agent.api.routes import router

    app = FastAPI(title="Lead Gen Agent", version="0.1.0", lifespan=_lifespan)
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(router)
    return app


app = create_app()
