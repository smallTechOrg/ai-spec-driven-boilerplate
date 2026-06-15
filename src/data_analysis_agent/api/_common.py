from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


def ok(data: Any) -> dict:
    return {"data": data, "error": None}


def api_error(code: str, message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(
        status_code=status_code, detail={"code": code, "message": message}
    )


def render(request: Request, templates: Jinja2Templates, name: str, **ctx) -> HTMLResponse:
    from data_analysis_agent.config.settings import get_settings
    ctx["llm_provider"] = get_settings().resolved_llm_provider
    ctx["request"] = request
    return templates.TemplateResponse(request, name, ctx)
