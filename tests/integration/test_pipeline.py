from fastapi.testclient import TestClient

from blogforge.api import create_app
from blogforge.db import repository as repo
from blogforge.domain import RunStatus
from blogforge.graph.runner import run_agent


def test_pipeline_end_to_end(db):
    voice = repo.create_voice(db, name="Sharp", description="Crisp", guidelines="- No fluff")
    writer = repo.create_writer(db, name="Alice", persona="Ex-engineer", voice_id=voice.id)

    result = run_agent(writer.id, "Why Rust scares me", notes=None)

    assert result.get("error") is None
    assert result.get("article_id")
    articles = repo.list_articles(db)
    assert len(articles) == 1
    # Body must look like an article, not just an outline of bullets.
    body = articles[0].body
    assert len(body) > 200, f"body too short to be an article: {body!r}"
    assert "##" in body or "\n\n" in body, f"body has no paragraph structure: {body!r}"
    # Title must be meaningful, not a bare placeholder.
    assert articles[0].title.strip() != ""
    assert articles[0].title.lower() != "title"

    from sqlalchemy import select
    from blogforge.db.models import AgentRunRow

    rows = db.execute(select(AgentRunRow)).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == RunStatus.completed.value


def test_golden_path_ui_flow(db):
    """Walks the full user journey through the UI and asserts the rendered
    article page actually looks like an article. This is the harness that
    catches 'it looks broken to a human' bugs that status-code-only tests miss.
    """
    client = TestClient(create_app())

    # Home page loads with nav
    home = client.get("/")
    assert home.status_code == 200
    assert "Voices" in home.text and "Writers" in home.text and "Articles" in home.text

    # Create voice
    r = client.post(
        "/voices",
        data={"name": "V1", "description": "crisp", "guidelines": "- no fluff"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    voice_id = repo.list_voices(db)[0].id

    # Voices list renders the new voice
    vlist = client.get("/voices")
    assert vlist.status_code == 200
    assert "V1" in vlist.text

    # Create writer — form must list the voice in the <select>
    wform = client.get("/writers/new")
    assert wform.status_code == 200
    assert str(voice_id) in wform.text and "V1" in wform.text

    r = client.post(
        "/writers",
        data={"name": "W1", "persona": "ex-engineer", "voice_id": str(voice_id)},
        follow_redirects=False,
    )
    assert r.status_code == 303
    writer_id = repo.list_writers(db)[0].id

    # Generate an article
    aform = client.get("/articles/new")
    assert aform.status_code == 200
    assert str(writer_id) in aform.text and "W1" in aform.text

    r = client.post(
        "/articles",
        data={"writer_id": str(writer_id), "topic": "Coffee rituals", "notes": ""},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    location = r.headers["location"]
    assert location.startswith("/articles/")
    article_id = location.rsplit("/", 1)[-1]

    # Detail page: the article must render as an article, not a stub stub.
    detail = client.get(f"/articles/{article_id}")
    assert detail.status_code == 200
    page = detail.text
    assert "Coffee rituals" in page, "topic missing from article page"
    assert "<article>" in page, "article tag missing"
    # The rendered body must have paragraph- or heading-level HTML — not just <ul>.
    assert ("<h2" in page or "<p>" in page), (
        "article body rendered without paragraph/heading structure — looks like a bare outline"
    )
    # Minimum content length after stripping nav chrome (rough sanity check).
    assert len(page) > 600, f"article page too short: {len(page)} chars"

    # Articles list shows the entry
    alist = client.get("/articles")
    assert alist.status_code == 200
    assert article_id in alist.text
