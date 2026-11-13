from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SessionCompleteRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=128)


class EvaluationOut(BaseModel):
    id: UUID
    audio_scores: dict | None = None
    knowledge_scores: dict | None = None
    audio_summary: str | None = None
    knowledge_summary: str | None = None
    overall_audio_score: float | None = None
    overall_knowledge_score: float | None = None
    model_meta: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: UUID
    internee_id: UUID
    internee_name: str
    elevenlabs_conversation_id: str | None = None
    agent_id: str
    status: str
    transcript_json: dict | list | None = None
    audio_gcs_url: str | None = None
    audio_content_type: str | None = None
    audio_play_url: str | None = None
    duration_secs: float | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    evaluation: EvaluationOut | None = None

    model_config = {"from_attributes": True}


class ResultsResponse(BaseModel):
    name: str
    sessions: list[SessionOut]


class UserResultsSummary(BaseModel):
    name: str
    session_count: int
    evaluated_count: int
    avg_audio_score: float | None = None
    avg_knowledge_score: float | None = None
    last_session_at: datetime | None = None


class ResultsSummaryResponse(BaseModel):
    users: list[UserResultsSummary]
