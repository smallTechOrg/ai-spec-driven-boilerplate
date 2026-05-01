from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


def render(request: Request, name: str, **ctx) -> HTMLResponse:
    """Starlette >=1.0 compatible TemplateResponse helper."""
    templates: Jinja2Templates = request.app.state.templates
    return templates.TemplateResponse(request, name, ctx)
