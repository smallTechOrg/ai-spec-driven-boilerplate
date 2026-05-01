from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class Writer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    persona: str
    voice_id: UUID
    created_at: datetime
