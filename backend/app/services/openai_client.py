from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import get_settings


def get_openai() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    settings = get_settings()
    client = get_openai()
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )
    # Ensure order matches input
    sorted_data = sorted(response.data, key=lambda d: d.index)
    return [list(item.embedding) for item in sorted_data]


def chat_json(system: str, user: str) -> dict[str, Any]:
    settings = get_settings()
    client = get_openai()
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
