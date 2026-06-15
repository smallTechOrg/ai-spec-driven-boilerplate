from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok"})
