from pathlib import Path
from uuid import UUID

import markdown as md
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from blogforge.db import repository as repo
from blogforge.db.session import new_session
from blogforge.graph.runner import run_agent


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
templates.env.filters["markdown"] = lambda text: md.markdown(text or "", extensions=["fenced_code", "tables"])

router = APIRouter()


def get_db():
    db = new_session()
    try:
        yield db
    finally:
        db.close()


def render(request: Request, name: str, **ctx):
    return templates.TemplateResponse(request, name, ctx)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    return render(
        request,
        "dashboard.html",
        voices=repo.list_voices(db),
        writers=repo.list_writers(db),
        articles=repo.list_articles(db, limit=5),
    )


# Voices ---------------------------------------------------------------------

@router.get("/voices", response_class=HTMLResponse)
def voices_index(request: Request, db: Session = Depends(get_db)):
    return render(request, "voices_list.html", voices=repo.list_voices(db))


@router.get("/voices/new", response_class=HTMLResponse)
def voices_new(request: Request):
    return render(request, "voice_form.html", error=None)


@router.post("/voices")
def voices_create(
    name: str = Form(...),
    description: str = Form(...),
    guidelines: str = Form(...),
    db: Session = Depends(get_db),
):
    repo.create_voice(db, name=name.strip(), description=description.strip(), guidelines=guidelines)
    return RedirectResponse("/voices", status_code=303)


# Writers --------------------------------------------------------------------

@router.get("/writers", response_class=HTMLResponse)
def writers_index(request: Request, db: Session = Depends(get_db)):
    return render(request, "writers_list.html", writers=repo.list_writers(db))


@router.get("/writers/new", response_class=HTMLResponse)
def writers_new(request: Request, db: Session = Depends(get_db)):
    return render(request, "writer_form.html", voices=repo.list_voices(db), error=None)


@router.post("/writers")
def writers_create(
    name: str = Form(...),
    persona: str = Form(...),
    voice_id: str = Form(...),
    db: Session = Depends(get_db),
):
    repo.create_writer(db, name=name.strip(), persona=persona, voice_id=UUID(voice_id))
    return RedirectResponse("/writers", status_code=303)


# Articles -------------------------------------------------------------------

@router.get("/articles", response_class=HTMLResponse)
def articles_index(request: Request, db: Session = Depends(get_db)):
    return render(request, "articles_list.html", articles=repo.list_articles(db))


@router.get("/articles/new", response_class=HTMLResponse)
def articles_new(request: Request, db: Session = Depends(get_db)):
    return render(request, "article_form.html", writers=repo.list_writers(db), error=None)


@router.post("/articles")
def articles_create(
    request: Request,
    writer_id: str = Form(...),
    topic: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    result = run_agent(UUID(writer_id), topic.strip(), notes.strip() or None)
    if result.get("error"):
        return templates.TemplateResponse(
            request,
            "article_form.html",
            {"writers": repo.list_writers(db), "error": result["error"]},
            status_code=500,
        )
    return RedirectResponse(f"/articles/{result['article_id']}", status_code=303)


@router.get("/articles/{article_id}", response_class=HTMLResponse)
def articles_detail(article_id: str, request: Request, db: Session = Depends(get_db)):
    article = repo.get_article(db, UUID(article_id))
    if article is None:
        raise HTTPException(404, "Article not found")
    return render(request, "article_detail.html", article=article)
