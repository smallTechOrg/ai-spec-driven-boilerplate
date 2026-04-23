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
    assert articles[0].title
    assert articles[0].body

    # AgentRun got marked completed
    from sqlalchemy import select
    from blogforge.db.models import AgentRunRow

    rows = db.execute(select(AgentRunRow)).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == RunStatus.completed.value


def test_http_flow(db):
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}

    r = client.post(
        "/voices",
        data={"name": "V1", "description": "d", "guidelines": "g"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    voice = repo.list_voices(db)[0]
    r = client.post(
        "/writers",
        data={"name": "W1", "persona": "p", "voice_id": str(voice.id)},
        follow_redirects=False,
    )
    assert r.status_code == 303

    writer = repo.list_writers(db)[0]
    r = client.post(
        "/articles",
        data={"writer_id": str(writer.id), "topic": "Coffee rituals", "notes": ""},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/articles/" in r.headers["location"]

    # article detail page renders
    article_id = r.headers["location"].rsplit("/", 1)[-1]
    r2 = client.get(f"/articles/{article_id}")
    assert r2.status_code == 200
    assert "Coffee rituals" in r2.text or "Stub" in r2.text
