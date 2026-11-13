from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.openai_client import chat_json
from app.services.rag import build_transcript_query, retrieve_relevant_chunks


SYSTEM_PROMPT = """You are an evaluator for internee customer-call practice.
Score the INTERNee (role=user) against company knowledge provided as retrieved context.
Return ONLY valid JSON with this schema:
{
  "factual_accuracy": 0-100,
  "coverage": 0-100,
  "hallucination": 0-100,
  "relevance": 0-100,
  "completeness": 0-100,
  "confidence_hedging": 0-100,
  "overall_knowledge_score": 0-100,
  "summary": "short paragraph",
  "citations": [{"chunk_id": "...", "quote": "..."}]
}
Rules:
- factual_accuracy: how well user statements match the knowledge context
- coverage: whether important company topics that came up were addressed correctly
- hallucination: HIGHER = more inventing unsupported facts (bad). Still include 0-100.
- relevance: stays on company/product topic
- completeness: answers with enough detail
- confidence_hedging: higher = clearer confident answers; lower = excessive hedging/reluctance in content
- If knowledge context is empty, score conservatively and note that no KB was available.
- Base judgments on the USER turns primarily.
"""


def evaluate_knowledge(
    db: Session,
    transcript: list[dict[str, Any]] | dict[str, Any] | None,
) -> dict[str, Any]:
    settings = get_settings()
    query = build_transcript_query(transcript)
    chunks = retrieve_relevant_chunks(db, query)
    context_blocks = []
    for c in chunks:
        context_blocks.append(f"[chunk_id={c['id']}]\n{c['content']}")
    context_text = "\n\n".join(context_blocks) if context_blocks else "(no knowledge base chunks retrieved)"

    # Compact transcript for the judge
    turns = transcript if isinstance(transcript, list) else (transcript or {}).get("transcript", [])
    dialog_lines = []
    for t in turns or []:
        role = t.get("role", "?")
        msg = (t.get("message") or "").strip()
        if msg:
            dialog_lines.append(f"{role}: {msg}")
    dialog = "\n".join(dialog_lines)[:12000]

    user_prompt = f"""Company knowledge context:
{context_text}

Call transcript:
{dialog}
"""

    if not settings.openai_api_key:
        return _fallback_scores(chunks, reason="OPENAI_API_KEY not configured")

    try:
        result = chat_json(SYSTEM_PROMPT, user_prompt)
    except Exception as exc:
        return _fallback_scores(chunks, reason=f"OpenAI evaluation failed: {exc}")

    # Normalize numeric fields
    keys = [
        "factual_accuracy",
        "coverage",
        "hallucination",
        "relevance",
        "completeness",
        "confidence_hedging",
        "overall_knowledge_score",
    ]
    for key in keys:
        try:
            result[key] = float(result.get(key, 0))
        except (TypeError, ValueError):
            result[key] = 0.0

    result["citations"] = result.get("citations") or []
    result["retrieved_chunk_ids"] = [c["id"] for c in chunks]
    result["summary"] = result.get("summary") or "Knowledge evaluation completed."
    result["model"] = settings.openai_chat_model
    return result


def _fallback_scores(chunks: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    return {
        "factual_accuracy": 0,
        "coverage": 0,
        "hallucination": 0,
        "relevance": 0,
        "completeness": 0,
        "confidence_hedging": 0,
        "overall_knowledge_score": 0,
        "summary": reason,
        "citations": [],
        "retrieved_chunk_ids": [c["id"] for c in chunks],
        "model": None,
    }
