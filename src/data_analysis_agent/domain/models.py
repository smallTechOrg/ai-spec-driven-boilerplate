from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4


def _uid() -> str:
    return str(uuid4())


class Dataset(BaseModel):
    id: str = Field(default_factory=_uid)
    filename: str
    file_path: str
    row_count: int | None = None
    column_names: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class QueryRecord(BaseModel):
    id: str = Field(default_factory=_uid)
    dataset_id: str
    question: str
    answer: str | None = None
    status: str = "pending"
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentRunRecord(BaseModel):
    id: str = Field(default_factory=_uid)
    query_record_id: str
    status: str = "pending"
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
