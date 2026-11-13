from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timezone

from app.db import SessionLocal
from app.models.evaluation import Evaluation
from app.models.session import SessionRecord, SessionStatus
from app.services import elevenlabs
from app.services.audio_eval import evaluate_audio
from app.services.eval_settings import filter_scores, get_or_create_settings
from app.services.gcs import upload_bytes
from app.services.knowledge_eval import evaluate_knowledge

logger = logging.getLogger(__name__)


def run_post_call_pipeline(session_id: str) -> None:
    asyncio.run(_run_post_call_pipeline_async(session_id))


async def _run_post_call_pipeline_async(session_id: str) -> None:
    db = SessionLocal()
    try:
        session = db.get(SessionRecord, uuid.UUID(session_id))
        if not session:
            logger.error("Session %s not found", session_id)
            return
        if not session.elevenlabs_conversation_id:
            session.status = SessionStatus.failed
            session.error_message = "Missing ElevenLabs conversation_id"
            db.commit()
            return

        session.status = SessionStatus.processing
        db.commit()

        conversation = await elevenlabs.wait_for_conversation_done(session.elevenlabs_conversation_id)
        if conversation.get("status") == "failed":
            session.status = SessionStatus.failed
            session.error_message = "ElevenLabs conversation failed"
            session.transcript_json = conversation
            db.commit()
            return

        transcript = conversation.get("transcript") or []
        session.transcript_json = transcript
        meta = conversation.get("metadata") or {}
        duration = meta.get("call_duration_secs") or meta.get("duration_secs")
        if duration is not None:
            try:
                session.duration_secs = float(duration)
            except (TypeError, ValueError):
                pass

        audio_bytes: bytes | None = None
        content_type = "audio/mpeg"
        if conversation.get("has_audio", True):
            try:
                audio_bytes, content_type = await elevenlabs.get_conversation_audio(
                    session.elevenlabs_conversation_id
                )
                ext = "mp3"
                if "wav" in content_type:
                    ext = "wav"
                object_path = f"audio/{session.id}/{session.elevenlabs_conversation_id}.{ext}"
                session.audio_gcs_url = upload_bytes(audio_bytes, object_path, content_type)
                session.audio_content_type = content_type
            except Exception as audio_exc:
                logger.warning("Audio fetch/upload failed: %s", audio_exc)

        # Evaluations (respect enabled parameter toggles from Settings)
        settings_row = get_or_create_settings(db)
        enabled = settings_row.enabled or {}

        audio_scores_raw = evaluate_audio(audio_bytes, transcript, session.duration_secs)
        knowledge_scores_raw = evaluate_knowledge(db, transcript)
        audio_scores = filter_scores(audio_scores_raw, enabled, "audio")
        knowledge_scores = filter_scores(knowledge_scores_raw, enabled, "knowledge")

        evaluation = db.query(Evaluation).filter(Evaluation.session_id == session.id).one_or_none()
        if evaluation is None:
            evaluation = Evaluation(session_id=session.id)
            db.add(evaluation)

        evaluation.audio_scores = audio_scores
        evaluation.knowledge_scores = knowledge_scores
        evaluation.audio_summary = audio_scores.get("summary")
        evaluation.knowledge_summary = knowledge_scores.get("summary")
        evaluation.overall_audio_score = (
            float(audio_scores["overall_audio_score"])
            if "overall_audio_score" in audio_scores and audio_scores["overall_audio_score"] is not None
            else None
        )
        evaluation.overall_knowledge_score = (
            float(knowledge_scores["overall_knowledge_score"])
            if "overall_knowledge_score" in knowledge_scores
            and knowledge_scores["overall_knowledge_score"] is not None
            else None
        )
        evaluation.model_meta = {
            "knowledge_model": knowledge_scores.get("model"),
            "retrieved_chunk_ids": knowledge_scores.get("retrieved_chunk_ids"),
            "agent_id": session.agent_id,
            "conversation_id": session.elevenlabs_conversation_id,
            "enabled_params": enabled,
        }

        session.status = SessionStatus.evaluated
        session.ended_at = datetime.now(timezone.utc)
        session.error_message = None
        db.commit()
        logger.info("Session %s evaluated successfully", session_id)
    except Exception as exc:
        logger.error("Pipeline failed for %s: %s\n%s", session_id, exc, traceback.format_exc())
        db.rollback()
        try:
            session = db.get(SessionRecord, uuid.UUID(session_id))
            if session:
                session.status = SessionStatus.failed
                session.error_message = str(exc)[:2000]
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
