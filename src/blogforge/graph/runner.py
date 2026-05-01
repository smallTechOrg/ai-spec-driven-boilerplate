from uuid import UUID

from blogforge.db import repository as repo
from blogforge.db.session import new_session
from blogforge.graph.agent import compiled_graph
from blogforge.graph.state import AgentState


def run_agent(writer_id: UUID, topic: str, notes: str | None = None) -> AgentState:
    with new_session() as db:
        writer = repo.get_writer(db, writer_id)
        if writer is None:
            raise ValueError(f"writer not found: {writer_id}")
        voice = repo.get_voice(db, writer.voice_id)
        if voice is None:
            raise ValueError(f"voice not found: {writer.voice_id}")
        run = repo.create_run(db, writer_id=writer_id, topic=topic)

    state: AgentState = {
        "run_id": str(run.id),
        "writer_id": str(writer.id),
        "voice_id": str(voice.id),
        "topic": topic,
        "notes": notes,
        "persona": writer.persona,
        "guidelines": voice.guidelines,
        "outline": None,
        "draft": None,
        "title": None,
        "body": None,
        "article_id": None,
        "error": None,
    }
    return compiled_graph.invoke(state)
