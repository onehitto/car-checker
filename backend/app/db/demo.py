"""Development demo data: `python -m app.cli seed --demo` (refused in production).

Everything goes through the application services, so linked expenses, odometer history,
schedules and alerts are exactly what real usage would produce. Dates are relative to today.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.config import Settings
from app.modules.alerts.reminders import ReminderService
from app.modules.alerts.schemas import ReminderCreate
from app.modules.audit.service import RequestMeta
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.service import AuthService, find_user_by_email
from app.modules.documents.models import DocumentType
from app.modules.documents.schemas import DocumentCreate
from app.modules.documents.service import DocumentService
from app.modules.expenses.models import ExpenseCategory
from app.modules.expenses.schemas import ExpenseCreate
from app.modules.expenses.service import ExpenseService
from app.modules.fuel.schemas import FuelRecordCreate
from app.modules.fuel.service import FuelService
from app.modules.garages.schemas import GarageCreate
from app.modules.garages.service import GarageService
from app.modules.maintenance.models import MaintenanceKind, MaintenanceType, OilType
from app.modules.maintenance.oil_changes import OilChangeService
from app.modules.maintenance.records import MaintenanceRecordService
from app.modules.maintenance.schedules import ScheduleService
from app.modules.maintenance.schemas import (
    MaintenanceRecordCreate,
    OilChangeCreate,
    ScheduleCreate,
)
from app.modules.mileage.schemas import MileageCreate
from app.modules.mileage.service import MileageService
from app.modules.notes.models import NoteCategory
from app.modules.notes.schemas import NoteCreate
from app.modules.notes.service import NoteService
from app.modules.parts.models import PartType
from app.modules.parts.schemas import PartCreate
from app.modules.parts.service import PartService
from app.modules.tires.models import TirePosition, TireSeason
from app.modules.tires.schemas import TireCreate
from app.modules.tires.service import TireService
from app.modules.users.models import User
from app.modules.vehicles.access import VehicleContext
from app.modules.vehicles.models import FuelType, TransmissionType, VehicleRole
from app.modules.vehicles.schemas import VehicleCreate
from app.modules.vehicles.service import VehicleService

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Car-checker-2026"  # noqa: S105 - documented development-only account


class DemoSeeder:
    def __init__(self, session: AsyncSession, settings: Settings, clock: Clock) -> None:
        self.session = session
        self.settings = settings
        self.clock = clock
        self.today = clock.today()

    def days_ago(self, days: int) -> date:
        return self.today - timedelta(days=days)

    async def run(self) -> bool:
        """Create the demo account and its vehicles. Returns False if it already exists."""
        if await find_user_by_email(self.session, DEMO_EMAIL):
            return False
        user, _ = await AuthService(self.session, self.settings, self.clock).register(
            RegisterRequest(
                email=DEMO_EMAIL,
                password=DEMO_PASSWORD,
                first_name="Demo",
                last_name="Driver",
                preferred_currency="EUR",
            ),
            RequestMeta(),
        )
        garage = await GarageService(self.session).create(
            user.id,
            GarageCreate(name="Garage Atlas", city="Casablanca", phone="+212 522 000 000"),
        )
        await self._logan(user, garage.id)
        await self._clio(user)
        return True

    async def _type_id(self, model: type[MaintenanceType] | type[PartType], code: str) -> uuid.UUID:
        type_id = await self.session.scalar(
            select(model.id).where(model.code == code, model.user_id.is_(None))
        )
        if type_id is None:
            raise RuntimeError(f"System type '{code}' missing: run `python -m app.cli seed`.")
        return type_id

    async def _logan(self, user: User, garage_id: uuid.UUID) -> None:
        vehicle = await VehicleService(self.session, self.clock).create(
            user,
            VehicleCreate(
                nickname="Family Logan",
                brand="Dacia",
                model="Logan",
                trim="Laureate",
                year=2019,
                license_plate="12345-A-6",
                vin="UU1LSDAAH12345678",
                fuel_type=FuelType.DIESEL,
                transmission_type=TransmissionType.MANUAL,
                engine="1.5 dCi",
                engine_displacement_cc=1461,
                horsepower=90,
                color="Grey",
                purchase_date=self.days_ago(1260),
                purchase_price=Decimal("8500.00"),
                initial_mileage=62_000,
                current_mileage=62_000,
            ),
        )
        ctx = VehicleContext(vehicle=vehicle, role=VehicleRole.OWNER, user=user)
        oil, records = (
            OilChangeService(self.session, self.clock),
            MaintenanceRecordService(self.session, self.clock),
        )

        for days, mileage in ((1080, 70_100), (720, 79_800), (360, 88_900), (200, 92_300)):
            await oil.create(
                ctx,
                OilChangeCreate(
                    service_date=self.days_ago(days),
                    mileage=mileage,
                    cost=Decimal("420.00"),
                    garage_id=garage_id,
                    oil_brand="Total Quartz",
                    oil_type=OilType.SYNTHETIC,
                    oil_viscosity="5W-30",
                    oil_quantity_liters=Decimal("4.80"),
                    oil_filter_changed=True,
                    filter_brand="Purflux",
                ),
            )
            if days == 720:
                await records.create(
                    ctx,
                    MaintenanceRecordCreate(
                        maintenance_type_id=await self._type_id(MaintenanceType, "repair"),
                        kind=MaintenanceKind.REPAIR,
                        title="Alternator replacement",
                        service_date=self.days_ago(650),
                        mileage=81_500,
                        labor_cost=Decimal("600.00"),
                        parts_cost=Decimal("1500.00"),
                        garage_id=garage_id,
                    ),
                )

        schedules = ScheduleService(self.session, self.clock)
        for code, fields in (
            ("oil_change", {}),
            ("brake_fluid", {"last_service_date": self.days_ago(800)}),
            (
                "timing_belt",
                {"last_service_date": self.days_ago(1260), "last_service_mileage": 62_000},
            ),
            ("vehicle_inspection", {"last_service_date": self.days_ago(350)}),
        ):
            await schedules.create(
                ctx,
                ScheduleCreate(
                    maintenance_type_id=await self._type_id(MaintenanceType, code),
                    **fields,
                ),
            )

        parts = PartService(self.session, self.clock)
        await parts.create(
            ctx,
            PartCreate(
                part_type_id=await self._type_id(PartType, "brake_pads"),
                brand="Bosch",
                reference_number="0 986 494 123",
                position="front",
                installed_date=self.days_ago(500),
                installed_mileage=85_000,
                price=Decimal("380.00"),
                labor_cost=Decimal("150.00"),
            ),
        )
        await parts.create(
            ctx,
            PartCreate(
                part_type_id=await self._type_id(PartType, "battery"),
                brand="Varta",
                installed_date=self.days_ago(1250),
                price=Decimal("900.00"),
                warranty_expiration_date=self.days_ago(520),
            ),
        )

        documents = DocumentService(self.session, self.clock)
        await documents.create(
            ctx,
            DocumentCreate(
                document_type=DocumentType.INSURANCE,
                title="Car insurance",
                provider="Wafa Assurance",
                document_number="POL-2025-0042",
                issue_date=self.days_ago(345),
                expiration_date=self.today + timedelta(days=20),
            ),
        )
        await documents.create(
            ctx,
            DocumentCreate(
                document_type=DocumentType.ROAD_TAX,
                title="Road tax",
                issue_date=self.days_ago(400),
                expiration_date=self.days_ago(35),
            ),
        )
        await documents.create(
            ctx,
            DocumentCreate(
                document_type=DocumentType.REGISTRATION,
                title="Registration certificate",
                document_number="12345-A-6",
                issue_date=self.days_ago(1260),
            ),
        )

        fuel = FuelService(self.session, self.clock)
        mileage = 92_300
        for index, days in enumerate(range(180, 0, -20)):
            mileage += 650 + (index % 3) * 40
            await fuel.create(
                ctx,
                FuelRecordCreate(
                    fill_date=self.days_ago(days),
                    mileage=mileage,
                    liters=Decimal("38.5") + index,
                    price_per_liter=Decimal("1.7900"),
                    full_tank=index % 4 != 2,
                    gas_station="Afriquia" if index % 2 else "Shell",
                ),
            )

        expenses = ExpenseService(self.session, self.clock)
        for category, title, amount, days in (
            (ExpenseCategory.PARKING, "Airport parking", "35.00", 120),
            (ExpenseCategory.TOLLS, "Highway Casablanca - Rabat", "23.00", 60),
            (ExpenseCategory.WASHING, "Car wash", "8.00", 15),
        ):
            await expenses.create(
                ctx,
                ExpenseCreate(
                    category=category,
                    title=title,
                    amount=Decimal(amount),
                    expense_date=self.days_ago(days),
                ),
            )

        tires = TireService(self.session, self.clock)
        for position in (
            TirePosition.FRONT_LEFT,
            TirePosition.FRONT_RIGHT,
            TirePosition.REAR_LEFT,
            TirePosition.REAR_RIGHT,
        ):
            await tires.create(
                ctx,
                TireCreate(
                    brand="Michelin",
                    model="Primacy 4",
                    size="185/65 R15 88T",
                    season=TireSeason.SUMMER,
                    position=position,
                    installed_date=self.days_ago(400),
                    tread_depth_mm=Decimal("4.5"),
                ),
            )
        await tires.create(
            ctx,
            TireCreate(brand="Continental", size="185/65 R15 88T", season=TireSeason.WINTER),
        )

        await MileageService(self.session, self.clock).add_reading(
            ctx, MileageCreate(mileage=mileage + 400), RequestMeta()
        )
        await ReminderService(self.session, self.clock).create(
            ctx,
            ReminderCreate(title="Renew parking badge", due_date=self.today + timedelta(days=5)),
        )
        await NoteService(self.session).create(
            ctx,
            NoteCreate(
                title="Rattling noise",
                body="Light rattle from the rear left when braking on rough roads.",
                category=NoteCategory.PROBLEM,
                is_pinned=True,
            ),
        )

    async def _clio(self, user: User) -> None:
        vehicle = await VehicleService(self.session, self.clock).create(
            user,
            VehicleCreate(
                brand="Renault",
                model="Clio",
                year=2016,
                fuel_type=FuelType.PETROL,
                license_plate="67890-B-1",
                purchase_date=self.days_ago(400),
                initial_mileage=120_000,
                current_mileage=120_000,
            ),
        )
        ctx = VehicleContext(vehicle=vehicle, role=VehicleRole.OWNER, user=user)
        await ScheduleService(self.session, self.clock).create(
            ctx,
            ScheduleCreate(
                maintenance_type_id=await self._type_id(MaintenanceType, "oil_change"),
                last_service_date=self.days_ago(390),
                last_service_mileage=120_000,
            ),
        )
        await MileageService(self.session, self.clock).add_reading(
            ctx, MileageCreate(mileage=131_200), RequestMeta()
        )
