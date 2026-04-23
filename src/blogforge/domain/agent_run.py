from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class RunStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class AgentRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    writer_id: UUID
    topic: str
    status: RunStatus
    article_id: UUID | None = None
    error_message: str | None = None
    created_at: datetime
