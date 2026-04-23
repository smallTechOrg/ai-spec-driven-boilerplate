from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Blog(BaseModel):
    id: int = 1
    name: str
    tagline: Optional[str] = None
    niche: str
    themes: list[str] = Field(default_factory=list)
    posts_per_run: int = 3
    schedule_cron: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class Writer(BaseModel):
    id: int
    name: str
    persona_prompt: str
    bio: str
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class Run(BaseModel):
    id: int
    trigger: str  # "manual" | "scheduled"
    status: str   # "running" | "completed" | "failed"
    posts_requested: int
    posts_completed: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class Post(BaseModel):
    id: int
    run_id: int
    writer_id: int
    topic: str
    title: str
    content_markdown: str
    content_html: str
    cover_image_path: Optional[str] = None
    cover_image_prompt: Optional[str] = None
    slug: str
    status: str = "success"  # "success" | "failed"
    published_at: Optional[datetime] = None
    created_at: datetime


class UsedTopic(BaseModel):
    id: int
    topic: str
    post_id: int
    used_at: datetime
