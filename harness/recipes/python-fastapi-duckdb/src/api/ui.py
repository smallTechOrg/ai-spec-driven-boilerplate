"""Server-rendered chat UI + a no-JS form fallback.

GET /        — renders the chat page (stub banner when in stub mode).
POST /run    — no-JS fallback: the HTML form posts here and re-renders the page
               with the result. The JS path POSTs JSON to /api/run instead.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.api.run import run_agent
from src.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory="src/api/templates")


def render(request: Request, name: str, **ctx) -> HTMLResponse:
    settings = get_settings()
    return templates.TemplateResponse(request, name, {"stub_mode": settings.is_stub, **ctx})


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return render(request, "index.html")


@router.post("/run", response_class=HTMLResponse)
async def run_form(request: Request):
    form = await request.form()
    user_input = (form.get("input") or "").strip()
    if not user_input:
        return render(request, "index.html", error="Please enter a message.")
    try:
        result, _run_id = await run_agent(user_input)
        return render(request, "index.html", input=user_input, result=result)
    except Exception as exc:
        return render(request, "index.html", input=user_input, error=str(exc))
