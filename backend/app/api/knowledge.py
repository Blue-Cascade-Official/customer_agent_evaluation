from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.knowledge import DocumentStatus, KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeDocumentOut
from app.services.gcs import upload_bytes
from app.services.rag import index_document

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


def _doc_out(doc: KnowledgeDocument, chunk_count: int = 0) -> KnowledgeDocumentOut:
    return KnowledgeDocumentOut(
        id=doc.id,
        filename=doc.filename,
        gcs_url=doc.gcs_url,
        mime_type=doc.mime_type,
        status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        error_message=doc.error_message,
        uploaded_at=doc.uploaded_at,
        chunk_count=chunk_count,
    )


@router.get("", response_model=list[KnowledgeDocumentOut])
def list_documents(db: Session = Depends(get_db)):
    docs = db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.uploaded_at.desc())).all()
    counts = dict(
        db.execute(
            select(KnowledgeChunk.document_id, func.count())
            .group_by(KnowledgeChunk.document_id)
        ).all()
    )
    return [_doc_out(d, int(counts.get(d.id, 0))) for d in docs]


@router.post("/upload", response_model=KnowledgeDocumentOut)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or "upload.bin"
    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    doc = KnowledgeDocument(
        filename=filename,
        mime_type=file.content_type,
        status=DocumentStatus.processing,
    )
    db.add(doc)
    db.flush()

    try:
        object_path = f"knowledge/{doc.id}/{filename}"
        doc.gcs_url = upload_bytes(data, object_path, file.content_type)
        chunk_count = index_document(db, doc, data)
        doc.status = DocumentStatus.ready
        doc.error_message = None
        db.commit()
        db.refresh(doc)
        return _doc_out(doc, chunk_count)
    except Exception as exc:
        doc.status = DocumentStatus.failed
        doc.error_message = str(exc)[:2000]
        db.commit()
        db.refresh(doc)
        raise HTTPException(status_code=500, detail=f"Failed to index document: {exc}") from exc


@router.delete("/{document_id}")
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"ok": True}
