from app.modules.dashboard.health import HealthLevel, health_score
from app.modules.documents.expiration import DocumentStatus
from app.modules.maintenance.calculator import DueStatus


def test_healthy_vehicle() -> None:
    health = health_score(
        [DueStatus.OK, DueStatus.UPCOMING], [DocumentStatus.VALID], [DueStatus.OK]
    )
    assert (health.score, health.level) == (100, HealthLevel.GOOD)


def test_penalties_and_counts() -> None:
    health = health_score(
        [DueStatus.OVERDUE, DueStatus.DUE, DueStatus.DUE_SOON],
        [DocumentStatus.EXPIRING_SOON],
        [DueStatus.DUE_SOON],
    )
    assert health.score == 100 - 25 - 10 - 5 - 5 - 5
    assert health.level is HealthLevel.ATTENTION
    assert (health.overdue_maintenance, health.due_maintenance) == (1, 2)
    assert (health.expiring_documents, health.worn_parts) == (1, 1)


def test_score_is_clamped_and_critical() -> None:
    health = health_score([DueStatus.OVERDUE] * 3, [DocumentStatus.EXPIRED] * 2, [])
    assert (health.score, health.level) == (0, HealthLevel.CRITICAL)
