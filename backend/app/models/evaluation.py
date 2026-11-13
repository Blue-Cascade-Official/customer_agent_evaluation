import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    audio_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    knowledge_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    audio_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_audio_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_knowledge_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("SessionRecord", back_populates="evaluation")
