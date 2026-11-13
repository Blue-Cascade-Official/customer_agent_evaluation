from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.session import SessionRecord
from app.services.gcs import read_bytes

router = APIRouter(prefix="/api/sessions", tags=["audio"])


@router.get("/{session_id}/audio")
def get_session_audio(session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = db.get(SessionRecord, session_id)
    if not session or not session.audio_gcs_url:
        raise HTTPException(status_code=404, detail="Audio not found")

    content_type = session.audio_content_type or "audio/mpeg"
    url = session.audio_gcs_url

    if url.startswith("file://"):
        path = Path(url.removeprefix("file://"))
        if not path.exists():
            raise HTTPException(status_code=404, detail="Local audio file missing")
        return FileResponse(path, media_type=content_type, filename=path.name)

    try:
        data = read_bytes(url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read audio: {exc}") from exc
    return Response(content=data, media_type=content_type)
