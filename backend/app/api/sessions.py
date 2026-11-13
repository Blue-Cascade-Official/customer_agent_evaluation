from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db import get_db
from app.models.internee import Internee
from app.models.session import SessionRecord, SessionStatus
from app.models.evaluation import Evaluation
from app.schemas.session import (
    EvaluationOut,
    ResultsResponse,
    ResultsSummaryResponse,
    SessionCompleteRequest,
    SessionCreateRequest,
    SessionOut,
    UserResultsSummary,
)
from app.services.elevenlabs import normalize_conversation_id
from app.services.gcs import signed_or_local_url
from app.workers.post_call_pipeline import run_post_call_pipeline

router = APIRouter(prefix="/api", tags=["sessions"])


def _session_out(session: SessionRecord) -> SessionOut:
    play_url = signed_or_local_url(session.audio_gcs_url)
    if session.audio_gcs_url and session.audio_gcs_url.startswith("file://"):
        play_url = f"/api/sessions/{session.id}/audio"

    evaluation = None
    if session.evaluation:
        evaluation = EvaluationOut.model_validate(session.evaluation)

    return SessionOut(
        id=session.id,
        internee_id=session.internee_id,
        internee_name=session.internee.name if session.internee else "",
        elevenlabs_conversation_id=session.elevenlabs_conversation_id,
        agent_id=session.agent_id,
        status=session.status.value if hasattr(session.status, "value") else str(session.status),
        transcript_json=session.transcript_json,
        audio_gcs_url=session.audio_gcs_url,
        audio_content_type=session.audio_content_type,
        audio_play_url=play_url,
        duration_secs=session.duration_secs,
        started_at=session.started_at,
        ended_at=session.ended_at,
        error_message=session.error_message,
        created_at=session.created_at,
        evaluation=evaluation,
    )


@router.post("/internees")
def create_or_find_internee(payload: SessionCreateRequest, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    # Prefer most recent matching name (case-insensitive) or create new
    existing = db.scalar(
        select(Internee).where(func.lower(Internee.name) == name.lower()).order_by(Internee.created_at.desc())
    )
    if existing:
        return {"id": str(existing.id), "name": existing.name}
    internee = Internee(name=name)
    db.add(internee)
    db.commit()
    db.refresh(internee)
    return {"id": str(internee.id), "name": internee.name}


@router.post("/sessions", response_model=SessionOut)
def create_session(payload: SessionCreateRequest, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    internee = Internee(name=name)
    db.add(internee)
    db.flush()

    settings = get_settings()
    session = SessionRecord(
        internee_id=internee.id,
        agent_id=settings.elevenlabs_agent_id,
        status=SessionStatus.ready,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    session = db.scalar(
        select(SessionRecord)
        .options(joinedload(SessionRecord.internee), joinedload(SessionRecord.evaluation))
        .where(SessionRecord.id == session.id)
    )
    return _session_out(session)


@router.post("/sessions/{session_id}/complete", response_model=SessionOut)
def complete_session(
    session_id: uuid.UUID,
    payload: SessionCompleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    session = db.scalar(
        select(SessionRecord)
        .options(joinedload(SessionRecord.internee), joinedload(SessionRecord.evaluation))
        .where(SessionRecord.id == session_id)
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.elevenlabs_conversation_id = normalize_conversation_id(payload.conversation_id)
    if not session.elevenlabs_conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")
    session.status = SessionStatus.processing
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    background_tasks.add_task(run_post_call_pipeline, str(session.id))
    return _session_out(session)


@router.post("/sessions/{session_id}/reprocess", response_model=SessionOut)
def reprocess_session(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Retry post-call ingest/evaluation (e.g. after fixing a bad conversation id)."""
    session = db.scalar(
        select(SessionRecord)
        .options(joinedload(SessionRecord.internee), joinedload(SessionRecord.evaluation))
        .where(SessionRecord.id == session_id)
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.elevenlabs_conversation_id:
        raise HTTPException(status_code=400, detail="Session has no conversation_id")

    session.elevenlabs_conversation_id = normalize_conversation_id(
        session.elevenlabs_conversation_id
    )
    session.status = SessionStatus.processing
    session.error_message = None
    db.commit()
    db.refresh(session)
    background_tasks.add_task(run_post_call_pipeline, str(session.id))
    return _session_out(session)


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = db.scalar(
        select(SessionRecord)
        .options(joinedload(SessionRecord.internee), joinedload(SessionRecord.evaluation))
        .where(SessionRecord.id == session_id)
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_out(session)


@router.get("/results/summary", response_model=ResultsSummaryResponse)
def get_results_summary(db: Session = Depends(get_db)):
    """Users table: one row per display name with average audio/knowledge scores."""
    name_key = func.lower(func.trim(Internee.name))
    display_name = func.min(Internee.name)
    rows = db.execute(
        select(
            name_key.label("name_key"),
            display_name.label("name"),
            func.count(SessionRecord.id).label("session_count"),
            func.count(Evaluation.id).label("evaluated_count"),
            func.avg(Evaluation.overall_audio_score).label("avg_audio_score"),
            func.avg(Evaluation.overall_knowledge_score).label("avg_knowledge_score"),
            func.max(SessionRecord.created_at).label("last_session_at"),
        )
        .select_from(SessionRecord)
        .join(Internee, SessionRecord.internee_id == Internee.id)
        .outerjoin(Evaluation, Evaluation.session_id == SessionRecord.id)
        .group_by(name_key)
        .order_by(func.max(SessionRecord.created_at).desc())
    ).all()

    users: list[UserResultsSummary] = []
    for row in rows:
        users.append(
            UserResultsSummary(
                name=row.name,
                session_count=int(row.session_count or 0),
                evaluated_count=int(row.evaluated_count or 0),
                avg_audio_score=(
                    round(float(row.avg_audio_score), 1)
                    if row.avg_audio_score is not None
                    else None
                ),
                avg_knowledge_score=(
                    round(float(row.avg_knowledge_score), 1)
                    if row.avg_knowledge_score is not None
                    else None
                ),
                last_session_at=row.last_session_at,
            )
        )
    return ResultsSummaryResponse(users=users)


@router.get("/results", response_model=ResultsResponse)
def get_results(name: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    name_clean = name.strip()
    sessions = db.scalars(
        select(SessionRecord)
        .join(Internee)
        .options(joinedload(SessionRecord.internee), joinedload(SessionRecord.evaluation))
        .where(func.lower(Internee.name) == name_clean.lower())
        .order_by(SessionRecord.created_at.desc())
    ).unique().all()
    return ResultsResponse(
        name=name_clean,
        sessions=[_session_out(s) for s in sessions],
    )
