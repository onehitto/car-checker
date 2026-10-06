"""Write audit entries for security-relevant actions (in the caller's transaction)."""

import ipaddress
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog

USER_AGENT_MAX_LENGTH = 512


@dataclass(frozen=True, slots=True)
class RequestMeta:
    """Client information attached to sessions and audit entries."""

    ip_address: str | None = None
    user_agent: str | None = None

    @classmethod
    def build(cls, ip_address: str | None, user_agent: str | None) -> "RequestMeta":
        try:
            valid_ip = str(ipaddress.ip_address(ip_address)) if ip_address else None
        except ValueError:
            valid_ip = None
        return cls(valid_ip, user_agent[:USER_AGENT_MAX_LENGTH] if user_agent else None)


def record_audit(
    session: AsyncSession,
    action: str,
    *,
    user_id: uuid.UUID | None,
    meta: RequestMeta | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add an audit entry; it is persisted with the caller's commit. Never pass secrets."""
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=meta.ip_address if meta else None,
            user_agent=meta.user_agent if meta else None,
            details=details or {},
        )
    )
