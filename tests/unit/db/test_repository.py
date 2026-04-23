from blogforge.db import repository as repo
from blogforge.domain import RunStatus


def test_voice_crud(db):
    v = repo.create_voice(db, name="Sharp Nerd", description="Crisp and technical", guidelines="- no fluff")
    assert v.id is not None
    fetched = repo.get_voice(db, v.id)
    assert fetched is not None and fetched.name == "Sharp Nerd"
    assert len(repo.list_voices(db)) == 1


def test_writer_crud(db):
    v = repo.create_voice(db, name="V", description="d", guidelines="g")
    w = repo.create_writer(db, name="Alice", persona="Ex-engineer", voice_id=v.id)
    assert w.voice_id == v.id
    assert repo.get_writer(db, w.id).name == "Alice"
    assert len(repo.list_writers(db)) == 1


def test_article_and_run_lifecycle(db):
    v = repo.create_voice(db, name="V", description="d", guidelines="g")
    w = repo.create_writer(db, name="Alice", persona="p", voice_id=v.id)

    run = repo.create_run(db, writer_id=w.id, topic="Rust lifetimes")
    assert run.status == RunStatus.pending

    article = repo.create_article(
        db,
        writer_id=w.id,
        voice_id=v.id,
        topic="Rust lifetimes",
        title="Rust Lifetimes Explained",
        body="# Body",
    )
    completed = repo.complete_run(db, run.id, article_id=article.id)
    assert completed.status == RunStatus.completed
    assert completed.article_id == article.id

    assert len(repo.list_articles(db)) == 1


def test_fail_run(db):
    v = repo.create_voice(db, name="V", description="d", guidelines="g")
    w = repo.create_writer(db, name="A", persona="p", voice_id=v.id)
    run = repo.create_run(db, writer_id=w.id, topic="T")
    failed = repo.fail_run(db, run.id, error_message="LLM down")
    assert failed.status == RunStatus.failed
    assert failed.error_message == "LLM down"
