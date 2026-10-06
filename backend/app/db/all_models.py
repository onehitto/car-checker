"""Import every ORM model so that `Base.metadata` is complete (Alembic autogenerate, tests)."""

from app.db.base import Base
from app.modules.alerts.models import Alert
from app.modules.attachments.models import Attachment
from app.modules.audit.models import AuditLog
from app.modules.auth.models import PasswordResetToken, RefreshToken, UserSession
from app.modules.documents.models import VehicleDocument
from app.modules.expenses.models import Expense
from app.modules.fuel.models import FuelRecord
from app.modules.garages.models import Garage
from app.modules.maintenance.models import (
    MaintenanceRecord,
    MaintenanceSchedule,
    MaintenanceType,
    OilChange,
)
from app.modules.mileage.models import MileageEntry
from app.modules.parts.models import PartReplacement, PartType
from app.modules.tires.models import Tire, TireEvent
from app.modules.users.models import User
from app.modules.vehicles.models import Vehicle, VehicleAccess

__all__ = [
    "Alert",
    "Attachment",
    "AuditLog",
    "Base",
    "Expense",
    "FuelRecord",
    "Garage",
    "MaintenanceRecord",
    "MaintenanceSchedule",
    "MaintenanceType",
    "MileageEntry",
    "OilChange",
    "PartReplacement",
    "PartType",
    "PasswordResetToken",
    "RefreshToken",
    "Tire",
    "TireEvent",
    "User",
    "UserSession",
    "Vehicle",
    "VehicleAccess",
    "VehicleDocument",
]
