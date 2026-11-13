import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SessionStatus(str, enum.Enum):
    ready = "ready"
    in_call = "in_call"
    processing = "processing"
    evaluated = "evaluated"
    failed = "failed"


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("internees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    elevenlabs_conversation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"),
        nullable=False,
        default=SessionStatus.ready,
    )
    transcript_json: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    audio_gcs_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    duration_secs: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    internee = relationship("Internee", back_populates="sessions")
    evaluation = relationship(
        "Evaluation",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
