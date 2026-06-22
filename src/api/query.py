import time
import uuid
from datetime import datetime, UTC

import aiosqlite
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config import get_settings
from src.integrations.llm import get_llm_client

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    session_id: str
    dataset_ids: list[str]
    question: str


@router.post("")
async def run_query(body: QueryRequest):
    settings = get_settings()

    # Validate question
    if not body.question.strip():
        return JSONResponse(status_code=422, content={"error": {"code": "BAD_INPUT", "message": "Question must not be empty"}})
    if len(body.question) > 2000:
        return JSONResponse(status_code=422, content={"error": {"code": "BAD_INPUT", "message": "Question exceeds 2000 characters"}})

    async with aiosqlite.connect(settings.sqlite_path) as db:
        db.row_factory = aiosqlite.Row

        # Validate session
        cursor = await db.execute("SELECT id FROM session WHERE id = ?", (body.session_id,))
        if not await cursor.fetchone():
            return JSONResponse(status_code=404, content={"error": {"code": "NO_SESSION", "message": "Session not found"}})

        # Validate datasets
        for did in body.dataset_ids:
            cursor = await db.execute(
                "SELECT id FROM dataset WHERE id = ? AND session_id = ?",
                (did, body.session_id),
            )
            if not await cursor.fetchone():
                return JSONResponse(status_code=404, content={"error": {"code": "NO_DATASET", "message": f"Dataset {did} not found"}})

    # Call LLM (stub in Phase 1)
    t0 = time.monotonic()
    result = await get_llm_client().complete([{"role": "user", "content": body.question}])
    duration_ms = int((time.monotonic() - t0) * 1000)

    run_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Write query_run + audit_log rows
    async with aiosqlite.connect(settings.sqlite_path) as db:
        await db.execute(
            "INSERT INTO query_run (id, session_id, question, sql, row_count, status, created_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, body.session_id, body.question, result.get("sql"), result.get("row_count"), "completed", now, now),
        )
        await db.execute(
            "INSERT INTO audit_log (id, run_id, session_id, action, payload, input_tokens, output_tokens, duration_ms, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), run_id, body.session_id, "llm", result.get("sql"), 0, 0, duration_ms, now),
        )
        await db.commit()

    return {
        "run_id": run_id,
        "sql": result["sql"],
        "rows": result["rows"],
        "columns": result["columns"],
        "row_count": result["row_count"],
        "table_markdown": result["table_markdown"],
        "chart_spec": result["chart_spec"],
        "suggestions": result["suggestions"],
        "summary": result.get("summary", ""),
    }


# Phase 2 deferred stub
@router.get("/{run_id}/audit")
async def get_audit(run_id: str):
    return JSONResponse(status_code=404, content={"error": {"code": "NOT_YET", "message": "Audit retrieval available in Phase 2"}})
