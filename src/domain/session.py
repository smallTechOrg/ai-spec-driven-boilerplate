from pydantic import BaseModel
from datetime import datetime


class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime
