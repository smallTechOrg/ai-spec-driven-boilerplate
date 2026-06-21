from fastapi import APIRouter

from src.config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "llm_provider": settings.resolved_llm_provider,
        "stub_mode": settings.is_stub,
    }
