/** Friendly aliases for the generated OpenAPI schemas. */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type User = Schemas["UserResponse"];
export type AuthResult = Schemas["AuthResponse"];
export type SessionInfo = Schemas["SessionResponse"];
export type Vehicle = Schemas["VehicleResponse"];
export type VehicleCreateBody = Schemas["VehicleCreate"];
export type VehicleUpdateBody = Schemas["VehicleUpdate"];
export type VehicleRole = Schemas["VehicleRole"];
export type MileageEntry = Schemas["MileageEntryResponse"];
export type Garage = Schemas["GarageResponse"];
export type MaintenanceType = Schemas["MaintenanceTypeResponse"];
export type MaintenanceRecord = Schemas["MaintenanceRecordResponse"];
export type MaintenanceSchedule = Schemas["ScheduleResponse"];
export type OilChange = Schemas["OilChangeResponse"];
export type PartType = Schemas["PartTypeResponse"];
export type Part = Schemas["PartResponse"];
export type Tire = Schemas["TireResponse"];
export type TireEvent = Schemas["TireEventResponse"];
export type VehicleDocument = Schemas["DocumentResponse"];
export type Expense = Schemas["ExpenseResponse"];
export type FuelRecord = Schemas["FuelRecordResponse"];
export type FuelStatistics = Schemas["FuelStatisticsResponse"];
export type Alert = Schemas["AlertResponse"];
export type AlertSummary = Schemas["AlertSummary"];
export type Reminder = Schemas["ReminderResponse"];
export type Note = Schemas["NoteResponse"];
export type Attachment = Schemas["AttachmentResponse"];
export type Share = Schemas["ShareResponse"];
export type TimelineEvent = Schemas["TimelineEventResponse"];
export type VehicleDashboard = Schemas["VehicleDashboard"];
export type GlobalDashboard = Schemas["GlobalDashboard"];
export type VehicleStatistics = Schemas["VehicleStatistics"];
export type GlobalStatistics = Schemas["GlobalStatistics"];
export type NotificationPreference = Schemas["PreferenceResponse"];
