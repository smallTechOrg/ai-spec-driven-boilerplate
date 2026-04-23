from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class Article(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    writer_id: UUID
    voice_id: UUID
    topic: str
    title: str
    body: str
    created_at: datetime
