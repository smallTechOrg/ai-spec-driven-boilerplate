"""FastAPI application factory."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from lead_gen_agent.api.routes import router
from lead_gen_agent.db import init_db
from lead_gen_agent.graph.progress import set_main_loop

import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_main_loop(asyncio.get_event_loop())
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="EU Lead Gen Agent", version="0.1.0", lifespan=lifespan)

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    app.include_router(router)
    return app
