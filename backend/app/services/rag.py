from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from pypdf import PdfReader
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.openai_client import embed_texts


def extract_text_from_bytes(data: bytes, filename: str, mime_type: str | None) -> str:
    lower = filename.lower()
    mime = (mime_type or "").lower()

    if lower.endswith(".pdf") or "pdf" in mime:
        reader = PdfReader(BytesIO(data))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()

    if lower.endswith(".docx") or "wordprocessingml" in mime:
        from docx import Document

        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text).strip()

    # Plain text / markdown / fallback
    return data.decode("utf-8", errors="ignore").strip()


def chunk_text(text_content: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text_content).strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def index_document(db: Session, document: KnowledgeDocument, data: bytes) -> int:
    text_content = extract_text_from_bytes(data, document.filename, document.mime_type)
    chunks = chunk_text(text_content)
    if not chunks:
        raise ValueError("No text could be extracted from the uploaded document")

    embeddings = embed_texts(chunks)
    # Clear existing chunks if re-indexing
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document.id).delete()
    for idx, (content, embedding) in enumerate(zip(chunks, embeddings)):
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=idx,
                content=content,
                embedding=embedding,
            )
        )
    db.flush()
    return len(chunks)


def retrieve_relevant_chunks(db: Session, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    k = top_k or settings.rag_top_k
    if not query.strip():
        return []

    # Ensure there is something to search
    count = db.scalar(select(KnowledgeChunk.id).limit(1))
    if count is None:
        return []

    query_embedding = embed_texts([query])[0]
    # Cosine distance with pgvector <=> operator
    sql = text(
        """
        SELECT id::text, document_id::text, chunk_index, content,
               embedding <=> CAST(:embedding AS vector) AS distance
        FROM knowledge_chunks
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :k
        """
    )
    # pgvector accepts vector literal as '[1,2,...]'
    emb_literal = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
    rows = db.execute(sql, {"embedding": emb_literal, "k": k}).mappings().all()
    return [
        {
            "id": row["id"],
            "document_id": row["document_id"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "distance": float(row["distance"]) if row["distance"] is not None else None,
        }
        for row in rows
    ]


def build_transcript_query(transcript: list[dict[str, Any]] | dict[str, Any] | None) -> str:
    turns = _normalize_turns(transcript)
    user_parts = [t["message"] for t in turns if t.get("role") == "user" and t.get("message")]
    if user_parts:
        return "\n".join(user_parts)[:6000]
    # Fallback to full dialog
    return "\n".join(f"{t.get('role')}: {t.get('message')}" for t in turns if t.get("message"))[:6000]


def _normalize_turns(transcript: list[dict[str, Any]] | dict[str, Any] | None) -> list[dict[str, Any]]:
    if transcript is None:
        return []
    if isinstance(transcript, list):
        return transcript
    if isinstance(transcript, dict):
        if isinstance(transcript.get("transcript"), list):
            return transcript["transcript"]
    return []
