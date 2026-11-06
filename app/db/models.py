from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class StoreSession(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    associate_id: Mapped[str] = mapped_column(String(100))
    store_id: Mapped[str] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(20), default="en")
    stage: Mapped[str] = mapped_column(String(40), default="assess")
    home_card: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)
    # Structured reply, provenance and media references can evolve with the dataset.
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WebhookInbox(Base):
    __tablename__ = "webhook_inbox"
    __table_args__ = (UniqueConstraint("phone_number_id", "message_id", name="uq_meta_message"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    phone_number_id: Mapped[str] = mapped_column(String(100))
    message_id: Mapped[str] = mapped_column(String(512))
    sender: Mapped[str] = mapped_column(String(50))
    message_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
