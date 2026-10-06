"""Import every ORM model so that `Base.metadata` is complete (Alembic autogenerate, tests)."""

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import PasswordResetToken, RefreshToken, UserSession
from app.modules.garages.models import Garage
from app.modules.maintenance.models import (
    MaintenanceRecord,
    MaintenanceSchedule,
    MaintenanceType,
)
from app.modules.mileage.models import MileageEntry
from app.modules.users.models import User
from app.modules.vehicles.models import Vehicle, VehicleAccess

__all__ = [
    "AuditLog",
    "Base",
    "Garage",
    "MaintenanceRecord",
    "MaintenanceSchedule",
    "MaintenanceType",
    "MileageEntry",
    "PasswordResetToken",
    "RefreshToken",
    "User",
    "UserSession",
    "Vehicle",
    "VehicleAccess",
]
