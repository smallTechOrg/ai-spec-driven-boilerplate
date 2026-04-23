import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class DBBlog(Base):
    __tablename__ = "blog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tagline: Mapped[str | None] = mapped_column(String(512), nullable=True)
    niche: Mapped[str] = mapped_column(String(255), nullable=False)
    themes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    posts_per_run: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    @property
    def themes(self) -> list[str]:
        return json.loads(self.themes_json)  # type: ignore[no-any-return]

    @themes.setter
    def themes(self, value: list[str]) -> None:
        self.themes_json = json.dumps(value)


class DBWriter(Base):
    __tablename__ = "writer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    persona_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    posts: Mapped[list["DBPost"]] = relationship("DBPost", back_populates="writer")


class DBRun(Base):
    __tablename__ = "run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    posts_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    posts_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    posts: Mapped[list["DBPost"]] = relationship("DBPost", back_populates="run")


class DBPost(Base):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("run.id"), nullable=False)
    writer_id: Mapped[int] = mapped_column(Integer, ForeignKey("writer.id"), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cover_image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped["DBRun"] = relationship("DBRun", back_populates="posts")
    writer: Mapped["DBWriter"] = relationship("DBWriter", back_populates="posts")
    used_topic: Mapped["DBUsedTopic | None"] = relationship("DBUsedTopic", back_populates="post", uselist=False)


class DBUsedTopic(Base):
    __tablename__ = "used_topic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("post.id"), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    post: Mapped["DBPost"] = relationship("DBPost", back_populates="used_topic")
