"""Attachment DTOs."""

import uuid
from datetime import datetime

from pydantic import Field

from app.core.schemas import ResponseModel
from app.modules.attachments.models import AttachmentEntity


class AttachmentResponse(ResponseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    entity_type: AttachmentEntity
    entity_id: uuid.UUID
    file_name: str
    content_type: str = Field(description="Detected from the file content.")
    file_size: int = Field(description="Bytes.")
    checksum_sha256: str
    user_id: uuid.UUID | None = Field(description="Uploader.")
    uploaded_at: datetime
