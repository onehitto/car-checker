/** Enum values of the API, in display order (checked against the generated schema). */
import type { components } from "./schema";

type Schemas = components["schemas"];

export const FUEL_TYPES = [
  "petrol",
  "diesel",
  "hybrid",
  "plug_in_hybrid",
  "electric",
  "lpg",
  "cng",
  "hydrogen",
  "other",
] as const satisfies readonly Schemas["FuelType"][];

export const TRANSMISSIONS = [
  "manual",
  "automatic",
  "semi_automatic",
  "cvt",
  "dual_clutch",
  "other",
] as const satisfies readonly Schemas["TransmissionType"][];

export const VEHICLE_STATUSES = [
  "active",
  "sold",
  "archived",
] as const satisfies readonly Schemas["VehicleStatus"][];

export const SHARED_ROLES = [
  "editor",
  "viewer",
] as const satisfies readonly Schemas["SharedRole"][];

export const MAINTENANCE_KINDS = [
  "maintenance",
  "repair",
] as const satisfies readonly Schemas["MaintenanceKind"][];

export const MAINTENANCE_CATEGORIES = [
  "engine",
  "filters",
  "fluids",
  "brakes",
  "electrical",
  "tires",
  "suspension",
  "transmission",
  "climate",
  "inspection",
  "body",
  "repair",
  "other",
] as const satisfies readonly Schemas["MaintenanceCategory"][];

export const PART_CATEGORIES = [
  "engine",
  "filters",
  "brakes",
  "electrical",
  "tires",
  "suspension",
  "transmission",
  "cooling",
  "lighting",
  "body",
  "other",
] as const satisfies readonly Schemas["PartCategory"][];

export const GARAGE_TYPES = [
  "garage",
  "mechanic",
  "dealership",
  "tire_shop",
  "body_shop",
  "inspection_center",
  "other",
] as const satisfies readonly Schemas["GarageType"][];

export const DOCUMENT_TYPES = [
  "insurance",
  "registration",
  "technical_inspection",
  "road_tax",
  "warranty",
  "leasing",
  "other",
] as const satisfies readonly Schemas["DocumentType"][];

export const DOCUMENT_STATUSES = [
  "valid",
  "expiring_soon",
  "expired",
] as const satisfies readonly Schemas["DocumentStatus"][];

export const EXPENSE_CATEGORIES = [
  "maintenance",
  "repairs",
  "parts",
  "fuel",
  "insurance",
  "taxes",
  "inspection",
  "registration",
  "parking",
  "tolls",
  "fines",
  "washing",
  "other",
] as const satisfies readonly Schemas["ExpenseCategory"][];

export const PUMP_FUELS = [
  "petrol",
  "diesel",
  "e85",
  "lpg",
  "cng",
  "hydrogen",
  "other",
] as const satisfies readonly Schemas["PumpFuel"][];

export const CONSUMPTION_UNITS = [
  "l_100km",
  "km_l",
  "mpg_us",
  "mpg_uk",
] as const satisfies readonly Schemas["ConsumptionUnit"][];

export const OIL_TYPES = [
  "synthetic",
  "semi_synthetic",
  "mineral",
  "high_mileage",
  "other",
] as const satisfies readonly Schemas["OilType"][];

export const TIRE_SEASONS = [
  "summer",
  "winter",
  "all_season",
] as const satisfies readonly Schemas["TireSeason"][];

export const TIRE_POSITIONS = [
  "front_left",
  "front_right",
  "rear_left",
  "rear_right",
  "spare",
] as const satisfies readonly Schemas["TirePosition"][];

export const TIRE_STATUSES = [
  "mounted",
  "stored",
  "discarded",
] as const satisfies readonly Schemas["TireStatus"][];

export const TIRE_CONDITIONS = [
  "new",
  "good",
  "fair",
  "worn",
  "damaged",
] as const satisfies readonly Schemas["TireCondition"][];

/** Events a user can log by hand (rotations are logged by the rotation form). */
export const TIRE_EVENT_TYPES = [
  "inspected",
  "repaired",
  "installed",
  "removed",
  "discarded",
] as const satisfies readonly Schemas["TireEventType"][];

export const NOTE_CATEGORIES = [
  "general",
  "maintenance",
  "repair",
  "part",
  "problem",
  "document",
] as const satisfies readonly Schemas["NoteCategory"][];

export const ALERT_STATUSES = [
  "active",
  "read",
  "dismissed",
  "resolved",
] as const satisfies readonly Schemas["AlertStatus"][];

export const ALERT_PRIORITIES = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
] as const satisfies readonly Schemas["AlertPriority"][];

export const ALERT_TYPES = [
  "maintenance_due",
  "document_expiration",
  "insurance_expiration",
  "inspection_due",
  "part_lifetime",
  "mileage_reminder",
  "custom_reminder",
  "system",
] as const satisfies readonly Schemas["AlertType"][];

export const TIMELINE_TYPES = [
  "maintenance",
  "repair",
  "part",
  "fuel",
  "expense",
  "document",
  "tire",
  "mileage",
] as const satisfies readonly Schemas["TimelineEventType"][];

export const ATTACHMENT_ENTITIES = [
  "vehicle",
  "maintenance_record",
  "part_replacement",
  "expense",
  "vehicle_document",
  "fuel_record",
  "tire",
] as const satisfies readonly Schemas["AttachmentEntity"][];
