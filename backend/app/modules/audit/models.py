"""Security audit trail."""

import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(sa.String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(sa.String(64))
    entity_id: Mapped[uuid.UUID | None]
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(sa.String(512))
    details: Mapped[dict[str, Any]] = mapped_column(
        default=dict, server_default=sa.text("'{}'::jsonb")
    )

    __table_args__ = (sa.Index(None, "user_id", "created_at"),)
