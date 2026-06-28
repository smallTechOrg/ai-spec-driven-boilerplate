from fastapi import APIRouter

from api._common import ok

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return ok({"status": "ok"})


@router.get("/api/health")
def api_health() -> dict:
    """Health check for the server and SQLite database connection."""
    from db.session import _get_engine
    from sqlalchemy import text

    db_status = "ok"
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return ok({"status": "ok", "db": db_status})
