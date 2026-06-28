from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/pg", tags=["pg"])


@router.post("/connect")
def connect_pg() -> dict:
    raise HTTPException(
        status_code=501,
        detail={
            "ok": False,
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": "PostgreSQL connection is coming in Phase 2.",
            },
        },
    )
