from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class PR(BaseModel):
    repo: str
    number: int
    title: str
    author: str
    days_open: int
    url: str

class Run(BaseModel):
    id: int
    ran_at: datetime
    status: str
    stale_pr_count: int
    error_message: Optional[str] = None
