from typing import TypedDict

from blogforge.domain.models import Blog, Post, Writer


class GenerationState(TypedDict):
    run_id: int
    blog: Blog
    posts_count: int
    topics: list[str]
    assignments: list[tuple[str, Writer]]
    completed_posts: list[Post]
    failed_topics: list[str]
    error: str | None
