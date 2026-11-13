from fastapi import APIRouter, HTTPException, Query

from app.services import elevenlabs

router = APIRouter(prefix="/api/elevenlabs", tags=["elevenlabs"])


@router.get("/conversation-token")
async def conversation_token(participant_name: str | None = Query(default=None)):
    try:
        data = await elevenlabs.get_conversation_token(participant_name=participant_name)
        return data
    except elevenlabs.ElevenLabsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
