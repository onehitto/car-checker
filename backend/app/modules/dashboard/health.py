"""Vehicle health score (pure). See docs/05-domain-logic.md, "Vehicle health score"."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from app.modules.documents.expiration import DocumentStatus
from app.modules.maintenance.calculator import DueStatus

SCHEDULE_PENALTY = {DueStatus.OVERDUE: 25, DueStatus.DUE: 10, DueStatus.DUE_SOON: 5}
DOCUMENT_PENALTY = {DocumentStatus.EXPIRED: 25, DocumentStatus.EXPIRING_SOON: 5}
PART_PENALTY = {DueStatus.OVERDUE: 10, DueStatus.DUE: 5, DueStatus.DUE_SOON: 5}


class HealthLevel(StrEnum):
    GOOD = "good"
    ATTENTION = "attention"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Health:
    score: int
    level: HealthLevel
    overdue_maintenance: int
    due_maintenance: int
    expired_documents: int
    expiring_documents: int
    worn_parts: int


def health_score(
    schedules: Iterable[DueStatus],
    documents: Iterable[DocumentStatus],
    parts: Iterable[DueStatus],
) -> Health:
    schedules, documents, parts = list(schedules), list(documents), list(parts)
    penalty = (
        sum(SCHEDULE_PENALTY.get(s, 0) for s in schedules)
        + sum(DOCUMENT_PENALTY.get(d, 0) for d in documents)
        + sum(PART_PENALTY.get(p, 0) for p in parts)
    )
    score = max(0, 100 - penalty)
    level = (
        HealthLevel.GOOD
        if score >= 80
        else HealthLevel.ATTENTION
        if score >= 50
        else HealthLevel.CRITICAL
    )
    return Health(
        score=score,
        level=level,
        overdue_maintenance=schedules.count(DueStatus.OVERDUE),
        due_maintenance=sum(s in (DueStatus.DUE, DueStatus.DUE_SOON) for s in schedules),
        expired_documents=documents.count(DocumentStatus.EXPIRED),
        expiring_documents=documents.count(DocumentStatus.EXPIRING_SOON),
        worn_parts=sum(p.is_at_least(DueStatus.DUE_SOON) for p in parts),
    )
