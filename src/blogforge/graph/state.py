from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    writer_id: str
    voice_id: str
    topic: str
    notes: str | None

    persona: str
    guidelines: str

    outline: str | None
    draft: str | None
    title: str | None
    body: str | None

    article_id: str | None
    error: str | None
