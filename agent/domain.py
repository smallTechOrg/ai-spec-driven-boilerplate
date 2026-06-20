import datetime as dt

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, _now, _uuid   # reuse the same declarative Base + helpers — do NOT define a second Base


class Ticket(Base):                 # one row per triaged support ticket
    __tablename__ = "tickets"
    id:          Mapped[str]  = mapped_column(String, primary_key=True, default=_uuid)
    run_id:      Mapped[str]  = mapped_column(ForeignKey("runs.id"), index=True)  # tie the row to its run
    subject:     Mapped[str | None] = mapped_column(String, nullable=True)
    body:        Mapped[str]  = mapped_column(Text)
    urgency:     Mapped[str | None] = mapped_column(String, nullable=True)   # low|normal|high|urgent
    category:    Mapped[str | None] = mapped_column(String, nullable=True)   # billing|technical|account|shipping|general
    draft_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at:  Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
