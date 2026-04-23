from fastapi import FastAPI

from blogforge.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="BlogForge")
    app.include_router(router)
    return app
