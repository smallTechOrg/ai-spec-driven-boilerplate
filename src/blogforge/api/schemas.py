from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BlogIn(BaseModel):
    name: Optional[str] = None
    tagline: Optional[str] = None
    niche: Optional[str] = None
    themes: Optional[list[str]] = None
    posts_per_run: Optional[int] = None
    schedule_cron: Optional[str] = None


class WriterIn(BaseModel):
    name: str
    persona_prompt: str
    bio: str
    avatar_url: Optional[str] = None


class WriterUpdate(BaseModel):
    name: Optional[str] = None
    persona_prompt: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None


class TriggerIn(BaseModel):
    posts_count: Optional[int] = None
