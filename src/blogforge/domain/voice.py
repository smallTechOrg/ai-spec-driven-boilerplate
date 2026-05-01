from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class Voice(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    guidelines: str
    created_at: datetime
