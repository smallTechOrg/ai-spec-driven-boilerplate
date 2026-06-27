from pydantic import BaseModel


class ColumnSchema(BaseModel):
    """One column's metadata — name + raw pandas dtype + friendly display label."""

    name: str
    dtype: str
    friendly_dtype: str


class UploadResponse(BaseModel):
    """Response for ``POST /datasets``.

    The ``schema`` field name is mandated by the api.md contract. It shadows the
    deprecated ``BaseModel.schema`` classmethod (Pydantic v2), which we never call,
    so the resulting warning is benign.
    """

    dataset_id: str
    filename: str
    row_count: int
    schema: list[ColumnSchema]


class AskRequest(BaseModel):
    """Request body for ``POST /datasets/{dataset_id}/ask``."""

    question: str


class AskResponse(BaseModel):
    """Response for ``POST /datasets/{dataset_id}/ask``.

    On failure, ``status`` is ``failed`` and ``error`` carries human-readable copy;
    the HTTP status stays 200 (graceful failure, never a crash).
    """

    run_id: str | None = None
    dataset_id: str
    status: str
    answer: str | None = None
    error: str | None = None
