from fastapi import APIRouter

from data_analyst.api._common import ok
from data_analyst.config.settings import get_settings

router = APIRouter()


@router.get("/health")
def health_check():
    settings = get_settings()
    return ok({
        "status": "ok",
        "version": "0.1.0",
        "llm_provider": settings.resolved_llm_provider,
    })
