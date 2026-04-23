from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class Email(BaseModel):
    id: str
    subject: str
    sender: str
    snippet: str

class EmailResult(BaseModel):
    id: Optional[int] = None
    email_id: str
    subject: str
    sender: str
    classification: str  # urgent / follow-up / ignore / error
    draft_reply: Optional[str] = None
    processed_at: datetime

class Run(BaseModel):
    id: int
    ran_at: datetime
    status: str
    emails_processed: int
    error_message: Optional[str] = None
