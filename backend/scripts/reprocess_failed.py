from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.models.session import SessionRecord, SessionStatus
from app.services.elevenlabs import normalize_conversation_id
from app.workers.post_call_pipeline import run_post_call_pipeline


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        sessions = db.scalars(
            select(SessionRecord)
            .where(SessionRecord.status == SessionStatus.failed)
            .order_by(SessionRecord.created_at.desc())
        ).all()
        if not sessions:
            print("No failed sessions")
            return
        for session in sessions:
            raw = session.elevenlabs_conversation_id or ""
            fixed = normalize_conversation_id(raw)
            print(f"Reprocessing {session.id}: {raw} -> {fixed}")
            session.elevenlabs_conversation_id = fixed
            session.status = SessionStatus.processing
            session.error_message = None
            db.commit()
            run_post_call_pipeline(str(session.id))
            db.refresh(session)
            print(f"  result status={session.status.value} error={session.error_message}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
