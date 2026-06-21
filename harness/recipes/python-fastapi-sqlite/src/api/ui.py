"""Server-rendered no-JS fallback UI.

The canonical UI is the Next.js agent-chat recipe (frontend-nextjs), which calls
the JSON contract in src/api/routes.py. This Jinja form is a zero-dependency
fallback that drives the SAME slice (graph -> echo tool -> stub LLM ->
persistence) and persists a Run row on submit.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.api.routes import run_agent
from src.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory="src/api/templates")


def render(request: Request, name: str, **ctx) -> HTMLResponse:
    settings = get_settings()
    return templates.TemplateResponse(
        request, name, {"stub_mode": settings.is_stub, **ctx}
    )


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return render(request, "index.html")


@router.post("/run", response_class=HTMLResponse)
async def run(request: Request):
    form = await request.form()
    user_input = (form.get("input") or "").strip()
    if not user_input:
        return render(request, "index.html", error="Please enter a message.")
    try:
        result, _run_id, error = await run_agent(user_input)
        if error:
            return render(request, "index.html", input=user_input, error=error)
        return render(request, "index.html", input=user_input, result=result)
    except Exception as exc:
        return render(request, "index.html", input=user_input, error=str(exc))
