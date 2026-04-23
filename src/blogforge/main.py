from contextlib import asynccontextmanager

from fastapi import FastAPI

from blogforge.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="BlogForge", lifespan=lifespan)
    return app


app = create_app()
