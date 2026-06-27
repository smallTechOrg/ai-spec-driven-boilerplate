from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    """Body of POST /datasets/{dataset_id}/ask."""
    question: str
    conversation_id: str = ""   # Phase 2: chat across turns; ignored in P1


class UploadResponse(BaseModel):
    """Response body for POST /datasets.

    The `schema` field name is mandated by spec/api.md; it intentionally shadows
    the pydantic BaseModel attribute, so the shadow warning is silenced here.
    """
    model_config = ConfigDict(protected_namespaces=())

    dataset_id: str
    filename: str
    row_count: int
    schema_: list[dict[str, Any]] = Field(serialization_alias="schema", alias="schema")
    sample_preview: list[dict[str, Any]]


class AskResponse(BaseModel):
    """Response body for POST /datasets/{dataset_id}/ask.

    Mirrors the dict returned by graph.runner.run_query. A graph-level failure
    arrives as status="failed" with a human-readable `error` and null compute
    fields — still a 200 envelope, never an HTTP 500.
    """
    query_id: str
    dataset_id: str
    status: str
    answer: str | None = None
    explanation: str | None = None
    code: str | None = None
    result: Any = None
    error: str | None = None
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    latency_ms: float | None = None
