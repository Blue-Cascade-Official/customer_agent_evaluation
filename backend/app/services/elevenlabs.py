from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from app.config import get_settings

BASE_URL = "https://api.elevenlabs.io"
_CONV_ID_RE = re.compile(r"(conv_[a-zA-Z0-9]+)")


class ElevenLabsError(RuntimeError):
    pass


def normalize_conversation_id(raw_id: str) -> str:
    """WebRTC often returns LiveKit room names like room_agent_…_conv_….

    The Conversations API expects the embedded conv_… id.
    """
    value = (raw_id or "").strip()
    if not value:
        return value
    match = _CONV_ID_RE.search(value)
    return match.group(1) if match else value


def _headers() -> dict[str, str]:
    settings = get_settings()
    if not settings.elevenlabs_api_key:
        raise ElevenLabsError("ELEVENLABS_API_KEY is not configured")
    return {"xi-api-key": settings.elevenlabs_api_key}


async def get_conversation_token(participant_name: str | None = None) -> dict[str, str]:
    settings = get_settings()
    params: dict[str, str] = {"agent_id": settings.elevenlabs_agent_id}
    if participant_name:
        params["participant_name"] = participant_name

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/v1/convai/conversation/token",
            params=params,
            headers=_headers(),
        )
    if response.status_code >= 400:
        raise ElevenLabsError(f"Token request failed: {response.status_code} {response.text}")
    data = response.json()
    return {"token": data["token"], "conversation_id": data.get("conversation_id", "")}


async def get_conversation(conversation_id: str) -> dict[str, Any]:
    cid = normalize_conversation_id(conversation_id)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{BASE_URL}/v1/convai/conversations/{cid}",
            headers=_headers(),
        )
    if response.status_code >= 400:
        raise ElevenLabsError(
            f"Get conversation failed: {response.status_code} {response.text}"
        )
    return response.json()


async def get_conversation_audio(conversation_id: str) -> tuple[bytes, str]:
    cid = normalize_conversation_id(conversation_id)
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            f"{BASE_URL}/v1/convai/conversations/{cid}/audio",
            headers=_headers(),
        )
    if response.status_code >= 400:
        raise ElevenLabsError(
            f"Get conversation audio failed: {response.status_code} {response.text}"
        )
    content_type = response.headers.get("content-type", "audio/mpeg")
    return response.content, content_type


async def wait_for_conversation_done(
    conversation_id: str,
    *,
    max_attempts: int = 40,
    delay_seconds: float = 3.0,
) -> dict[str, Any]:
    cid = normalize_conversation_id(conversation_id)
    last: dict[str, Any] | None = None
    for _ in range(max_attempts):
        last = await get_conversation(cid)
        status = last.get("status")
        if status in {"done", "failed"}:
            return last
        await asyncio.sleep(delay_seconds)
    raise ElevenLabsError(
        f"Conversation {cid} did not finish in time (last={last and last.get('status')})"
    )

