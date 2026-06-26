from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConversationSession(BaseModel):
    """Public read shape of a `ConversationSessionRow`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str | None = None
    dataset_ids_json: list[str] | None = None
    name: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionRenameRequest(BaseModel):
    """Body for `PATCH /sessions/{id}/name`."""

    name: str | None = Field(default=None, max_length=200)


class SessionTurn(BaseModel):
    """One conversation turn — a `query_runs` row exposed to the UI.

    `type` is `"clarification"` when the run short-circuited at pre-flight, else
    `"answer"`. `clarification_question` carries the asked question for a
    clarification turn (it lives in the `answer` field of the row), else null.
    """

    run_id: str
    question: str
    answer_markdown: str
    answer_html: str
    iteration_count: int
    tokens_input: int
    tokens_output: int
    status: str
    type: str
    clarification_question: str | None = None
    steps: list[Any] = Field(default_factory=list)
    dataset_ids: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    prompt_breakdown: dict[str, Any] = Field(default_factory=dict)


class SessionListItem(BaseModel):
    """One row in `GET /sessions` — a session plus turn summary."""

    id: str
    name: str | None = None
    dataset_id: str | None = None
    dataset_ids: list[str] = Field(default_factory=list)
    turn_count: int = 0
    first_question: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionDetail(BaseModel):
    """`GET /sessions/{id}` — a session plus its ordered turns."""

    id: str
    name: str | None = None
    dataset_id: str | None = None
    dataset_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    turns: list[SessionTurn] = Field(default_factory=list)
