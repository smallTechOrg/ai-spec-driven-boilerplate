"""POST /api/run — the JSON vertical slice.

UI -> API -> LangGraph ReAct loop -> echo tool -> stub LLM -> SQLite persistence
(+ one DuckDB event write) -> response. Contract:

  request : { "input": <text> }
  response: { "ok": true, "data": { "result": <string>, "run_id": <id> } }
"""

from fastapi import APIRouter
from pydantic import BaseModel

from src.api.run import run_agent

router = APIRouter()


class RunRequest(BaseModel):
    input: str


@router.post("/api/run")
async def run(req: RunRequest) -> dict:
    result, run_id = await run_agent(req.input)
    return {"ok": True, "data": {"result": result, "run_id": run_id}}
