"""Legacy runs endpoint — not used by the analyst agent."""
from fastapi import APIRouter
from api._common import api_error

router = APIRouter()


@router.post("/runs")
def create_run():
    raise api_error("NOT_IMPLEMENTED", "Use /chat for the analyst agent", 501)


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    raise api_error("NOT_IMPLEMENTED", "Use /chat for the analyst agent", 501)
