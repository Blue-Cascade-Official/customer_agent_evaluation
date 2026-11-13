from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class KnowledgeDocumentOut(BaseModel):
    id: UUID
    filename: str
    gcs_url: str | None = None
    mime_type: str | None = None
    status: str
    error_message: str | None = None
    uploaded_at: datetime
    chunk_count: int = 0

    model_config = {"from_attributes": True}
