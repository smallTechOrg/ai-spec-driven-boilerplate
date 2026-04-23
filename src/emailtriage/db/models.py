from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class DBEmailResult(Base):
    __tablename__ = "email_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email_id: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    sender: Mapped[str] = mapped_column(String(500), nullable=False)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    draft_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

class DBRun(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ran_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    emails_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
