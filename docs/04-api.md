# 10–12, 19, 27. API reference

Base URL: `/api/v1`. All endpoints except `auth/register`, `auth/login`,
`auth/refresh`, `auth/password/*` and health checks require
`Authorization: Bearer <access_token>`.

The OpenAPI document generated from the code (`/openapi.json`, Swagger UI at
`/docs`) is the exhaustive, always up-to-date contract. This page is the
overview.

Legend for the "Role" column on vehicle routes: **V** viewer, **E** editor,
**O** owner — the minimum vehicle role required.

## 10. Endpoint list

### Health
| Method | Path              | Description                          |
|--------|-------------------|--------------------------------------|
| GET    | `/health`         | Liveness + database check (no auth)  |
| GET    | `/api/v1/health`  | Same, versioned                      |

### Auth
| Method | Path                       | Description                                        |
|--------|----------------------------|----------------------------------------------------|
| POST   | `/auth/register`           | Create account, returns user + tokens (201)        |
| POST   | `/auth/login`              | Email + password → tokens                          |
| POST   | `/auth/refresh`            | Rotate refresh token → new token pair              |
| POST   | `/auth/logout`             | Revoke current session (204)                       |
| POST   | `/auth/logout-all`         | Revoke every session of the user (204)             |
| POST   | `/auth/password/forgot`    | Send reset email; always 202                       |
| POST   | `/auth/password/reset`     | Token + new password; revokes all sessions (204)   |
| POST   | `/auth/password/change`    | Current + new password; revokes other sessions (204) |

### Current user
| Method | Path                                   | Description                               |
|--------|----------------------------------------|-------------------------------------------|
| GET    | `/users/me`                            | Profile                                   |
| PATCH  | `/users/me`                            | Update profile & preferences              |
| DELETE | `/users/me`                            | Delete account (password confirmation)    |
| GET    | `/users/me/sessions`                   | Active sessions                           |
| DELETE | `/users/me/sessions/{session_id}`      | Revoke a session                          |
| GET    | `/users/me/notification-preferences`   | Notification preferences                  |
| PUT    | `/users/me/notification-preferences`   | Replace notification preferences          |

### Vehicles & sharing
| Method | Path                                        | Role | Description                             |
|--------|---------------------------------------------|------|-----------------------------------------|
| GET    | `/vehicles`                                 | —    | Own + shared vehicles (`status`, `q`, `role`, sort, pagination) |
| POST   | `/vehicles`                                 | —    | Create                                  |
| GET    | `/vehicles/{vehicle_id}`                    | V    | Details incl. caller's `access_role`    |
| PATCH  | `/vehicles/{vehicle_id}`                    | E    | Update                                  |
| DELETE | `/vehicles/{vehicle_id}`                    | O    | Delete with all history                 |
| GET    | `/vehicles/{vehicle_id}/access`             | O    | List shares                             |
| POST   | `/vehicles/{vehicle_id}/access`             | O    | Share with a registered user by email   |
| PATCH  | `/vehicles/{vehicle_id}/access/{access_id}` | O    | Change role                             |
| DELETE | `/vehicles/{vehicle_id}/access/{access_id}` | O*   | Revoke (*a grantee may remove themself) |

### Mileage
| Method | Path                                          | Role | Description                                 |
|--------|-----------------------------------------------|------|---------------------------------------------|
| GET    | `/vehicles/{vehicle_id}/mileage`              | V    | History (date range, pagination)            |
| POST   | `/vehicles/{vehicle_id}/mileage`              | E    | New reading; updates `current_mileage`      |
| DELETE | `/vehicles/{vehicle_id}/mileage/{entry_id}`   | E    | Delete a reading; current mileage recomputed |

### Garages
| Method | Path                     | Description        |
|--------|--------------------------|--------------------|
| GET    | `/garages`               | List (`q`, `garage_type`, `city`) |
| POST   | `/garages`               | Create             |
| GET    | `/garages/{garage_id}`   | Details            |
| PATCH  | `/garages/{garage_id}`   | Update             |
| DELETE | `/garages/{garage_id}`   | Delete (history keeps the record, garage set to null) |

### Maintenance types & part types (catalogs)
| Method | Path                                    | Description                         |
|--------|-----------------------------------------|-------------------------------------|
| GET    | `/maintenance-types`                    | System + own custom types           |
| POST   | `/maintenance-types`                    | Create custom type                  |
| PATCH  | `/maintenance-types/{type_id}`          | Update own custom type              |
| DELETE | `/maintenance-types/{type_id}`          | Delete own custom type (409 if used) |
| GET/POST/PATCH/DELETE | `/part-types[/{type_id}]` | Same for part types               |

### Maintenance records, oil changes, schedules
| Method | Path                                                          | Role | Description |
|--------|---------------------------------------------------------------|------|-------------|
| GET    | `/maintenance`                                                | —    | Records across accessible vehicles (`vehicle_id` filter + all filters below) |
| GET    | `/vehicles/{vehicle_id}/maintenance`                          | V    | Filters: `maintenance_type_id`, `kind`, `garage_id`, `date_from`, `date_to`, `mileage_min`, `mileage_max`, `cost_min`, `cost_max`, `q`; sort `service_date`, `mileage`, `cost`, `created_at` |
| POST   | `/vehicles/{vehicle_id}/maintenance`                          | E    | Create (updates schedule, mileage, linked expense) |
| GET    | `/vehicles/{vehicle_id}/maintenance/{record_id}`              | V    | Details |
| PATCH  | `/vehicles/{vehicle_id}/maintenance/{record_id}`              | E    | Update |
| DELETE | `/vehicles/{vehicle_id}/maintenance/{record_id}`              | E    | Delete |
| GET    | `/vehicles/{vehicle_id}/oil-changes`                          | V    | Oil change history |
| POST   | `/vehicles/{vehicle_id}/oil-changes`                          | E    | Create oil change (maintenance record + oil details) |
| GET/PATCH/DELETE | `/vehicles/{vehicle_id}/oil-changes/{record_id}`    | V/E/E | |
| GET    | `/vehicles/{vehicle_id}/maintenance-schedules`                | V    | Schedules with computed status (`status` filter) |
| POST   | `/vehicles/{vehicle_id}/maintenance-schedules`                | E    | Create |
| GET/PATCH/DELETE | `/vehicles/{vehicle_id}/maintenance-schedules/{schedule_id}` | V/E/E | |

### Parts & tires
| Method | Path                                                     | Role | Description |
|--------|----------------------------------------------------------|------|-------------|
| GET    | `/vehicles/{vehicle_id}/parts`                           | V    | Filters: `part_type_id`, `installed` (current only), `date_from`, `date_to`, `q` |
| POST   | `/vehicles/{vehicle_id}/parts`                           | E    | Record a replacement |
| GET/PATCH/DELETE | `/vehicles/{vehicle_id}/parts/{part_id}`       | V/E/E | Includes lifetime status |
| GET    | `/vehicles/{vehicle_id}/tires`                           | V    | Filter `status`, `season` |
| POST   | `/vehicles/{vehicle_id}/tires`                           | E    | Add a tire (creates `installed` event when mounted) |
| GET/PATCH/DELETE | `/vehicles/{vehicle_id}/tires/{tire_id}`       | V/E/E | |
| POST   | `/vehicles/{vehicle_id}/tires/rotations`                 | E    | Rotate several tires atomically |
| GET    | `/vehicles/{vehicle_id}/tires/{tire_id}/events`          | V    | Tire history |
| POST   | `/vehicles/{vehicle_id}/tires/{tire_id}/events`          | E    | Inspection, repair, removal, … |

### Documents
| Method | Path                                                   | Role | Description |
|--------|--------------------------------------------------------|------|-------------|
| GET    | `/documents`                                           | —    | Across vehicles (`vehicle_id`, `document_type`, `status`, `expires_before`) |
| GET    | `/vehicles/{vehicle_id}/documents`                     | V    | Same filters |
| POST   | `/vehicles/{vehicle_id}/documents`                     | E    | Create |
| GET/PATCH/DELETE | `/vehicles/{vehicle_id}/documents/{document_id}` | V/E/E | Includes `status`, `days_until_expiration` |

### Alerts & reminders
| Method | Path                                                | Role | Description |
|--------|-----------------------------------------------------|------|-------------|
| GET    | `/alerts`                                           | —    | Own alerts (`vehicle_id`, `priority`, `status`, `alert_type`) |
| GET    | `/alerts/summary`                                   | —    | Counts of open alerts by priority |
| POST   | `/alerts/read-all`                                  | —    | Mark all active alerts as read |
| GET    | `/alerts/{alert_id}`                                | —    | Details |
| PATCH  | `/alerts/{alert_id}`                                | —    | `status`: `read`, `dismissed`, `resolved`, or `active` (unread) |
| GET    | `/vehicles/{vehicle_id}/alerts`                     | V    | Own alerts for a vehicle |
| GET    | `/vehicles/{vehicle_id}/reminders`                  | V    | Custom reminders |
| POST   | `/vehicles/{vehicle_id}/reminders`                  | E    | Create |
| GET    | `/vehicles/{vehicle_id}/reminders/{reminder_id}`    | V    | Details with computed status |
| PATCH/DELETE | `/vehicles/{vehicle_id}/reminders/{reminder_id}` | E | Update, complete (`completed: true`), reopen, delete |

### Expenses & fuel
| Method | Path                                              | Role | Description |
|--------|---------------------------------------------------|------|-------------|
| GET    | `/expenses`                                       | —    | Across vehicles (`vehicle_id`, `category`, `date_from`, `date_to`, `amount_min`, `amount_max`, `q`) |
| GET    | `/vehicles/{vehicle_id}/expenses`                 | V    | Same filters + `source` (`manual`, `maintenance`, `part`, `fuel`) |
| POST   | `/vehicles/{vehicle_id}/expenses`                 | E    | Create |
| GET/PATCH/DELETE | `/vehicles/{vehicle_id}/expenses/{expense_id}` | V/E/E | Linked expenses are read-only (409) |
| GET    | `/vehicles/{vehicle_id}/fuel`                     | V    | Fill-ups with per-fill consumption |
| POST   | `/vehicles/{vehicle_id}/fuel`                     | E    | Create (linked expense, mileage update) |
| GET/PATCH/DELETE | `/vehicles/{vehicle_id}/fuel/{fuel_id}`  | V/E/E | |
| GET    | `/vehicles/{vehicle_id}/fuel/statistics`          | V    | Averages, cost/km, monthly spending |

### Attachments & notes
| Method | Path                                                              | Role | Description |
|--------|-------------------------------------------------------------------|------|-------------|
| GET    | `/vehicles/{vehicle_id}/attachments`                              | V    | Filter `entity_type`, `entity_id` |
| POST   | `/vehicles/{vehicle_id}/attachments`                              | E    | `multipart/form-data`: `file`, `entity_type`, `entity_id` |
| GET    | `/vehicles/{vehicle_id}/attachments/{attachment_id}`              | V    | Metadata |
| GET    | `/vehicles/{vehicle_id}/attachments/{attachment_id}/download`     | V    | File stream |
| DELETE | `/vehicles/{vehicle_id}/attachments/{attachment_id}`              | E    | |
| PUT    | `/vehicles/{vehicle_id}/image`                                    | E    | Upload / replace vehicle picture |
| DELETE | `/vehicles/{vehicle_id}/image`                                    | E    | |
| GET/POST | `/vehicles/{vehicle_id}/notes`                                  | V/E  | Filter `category`, `entity_type`, `entity_id`, `q` |
| GET/PATCH/DELETE | `/vehicles/{vehicle_id}/notes/{note_id}`                | V/E/E | |

### Timeline, dashboard, statistics
| Method | Path                                     | Role | Description |
|--------|------------------------------------------|------|-------------|
| GET    | `/vehicles/{vehicle_id}/timeline`        | V    | Chronological history; `type` (repeatable), `date_from`, `date_to`, pagination |
| GET    | `/vehicles/{vehicle_id}/dashboard`       | V    | Vehicle dashboard |
| GET    | `/dashboard`                             | —    | All vehicles of the user |
| GET    | `/vehicles/{vehicle_id}/statistics`      | V    | `date_from`, `date_to` or `year`, `category` (repeatable) |
| GET    | `/statistics`                            | —    | Across vehicles, grouped by currency (`vehicle_id` filter) |

## 11. Request and response DTOs (main schemas)

Field lists below are abbreviated; types follow the database design. All
request bodies reject unknown fields. Responses never include internal columns
such as `password_hash` or `token_hash`.

```jsonc
// RegisterRequest
{ "email": "str", "password": "str(8-128)", "first_name": "str", "last_name": "str",
  "phone_number": "str?", "preferred_language": "en|fr|ar?", "preferred_currency": "ISO-4217?",
  "preferred_distance_unit": "km|mi?", "timezone": "IANA?" }

// AuthResponse
{ "user": UserResponse, "tokens": { "access_token": "jwt", "refresh_token": "opaque",
  "token_type": "bearer", "expires_in": 900, "refresh_expires_in": 2592000 } }

// VehicleCreate / VehicleResponse (+ id, owner_id, access_role, created_at, updated_at)
{ "nickname": "str?", "brand": "str", "model": "str", "trim": "str?", "year": 2019,
  "license_plate": "str?", "vin": "str?", "fuel_type": "diesel", "transmission_type": "manual?",
  "engine": "str?", "engine_displacement_cc": 1461, "horsepower": 90, "color": "str?",
  "purchase_date": "date?", "purchase_price": "decimal?", "currency": "EUR?",
  "initial_mileage": 80000, "current_mileage": 80000, "status": "active", "notes": "str?" }

// MileageCreate (POST /vehicles/{id}/mileage)
{ "mileage": 59400, "recorded_on": "date? (default today)", "notes": "str?",
  "record_history": true, "force": false }

// MaintenanceRecordCreate / Response (+ id, vehicle_id, maintenance_type{}, garage{}, expense_id)
{ "maintenance_type_id": "uuid", "kind": "maintenance|repair", "title": "str",
  "description": "str?", "service_date": "date", "mileage": 60000, "cost": "decimal?",
  "labor_cost": "decimal?", "parts_cost": "decimal?", "garage_id": "uuid?", "notes": "str?" }

// MaintenanceScheduleResponse
{ "id": "uuid", "maintenance_type": {...}, "interval_km": 10000, "interval_months": 12,
  "last_service_date": "2025-11-01", "last_service_mileage": 50000,
  "next_service_date": "2026-11-01", "next_service_mileage": 60000,
  "warning_before_km": 1000, "warning_before_days": 30, "enabled": true,
  "remaining_km": 600, "remaining_days": 26, "overdue_km": 0, "overdue_days": 0,
  "status": "due_soon", "due_reason": "both" }

// DocumentResponse
{ "id": "uuid", "document_type": "insurance", "title": "str", "expiration_date": "date?",
  "reminder_days": [30, 7, 1, 0], "status": "valid|expiring_soon|expired",
  "days_until_expiration": 12, ... }

// AlertResponse
{ "id": "uuid", "vehicle_id": "uuid?", "alert_type": "maintenance_due", "title": "str",
  "message": "str", "template_key": "str", "template_params": {}, "priority": "high",
  "status": "active", "trigger_date": "date?", "trigger_mileage": 60000,
  "read_at": null, "resolved_at": null, "created_at": "datetime" }

// FuelRecordResponse (+ computed)
{ "fill_date": "date", "mileage": 60250, "liters": "42.300", "price_per_liter": "1.8900",
  "total_price": "79.95", "full_tank": true, "distance_since_previous": 610,
  "consumption_l_100km": 6.93, ... }
```

Monetary values are serialized as **decimal strings** (`"79.95"`) to avoid
floating-point loss in clients.

## 12. Validation rules

| Field / rule                     | Constraint                                                                       |
|----------------------------------|----------------------------------------------------------------------------------|
| Email                            | RFC-valid (`email-validator`), normalized to lower case, unique                  |
| Password                         | 8–128 chars, ≥ 1 letter and ≥ 1 digit, must not contain the email local part     |
| Names                            | 1–100 chars, trimmed                                                             |
| Language / units                 | Enumerations (`en/fr/ar`, `km/mi`, `l_100km/km_l/mpg_us/mpg_uk`)                 |
| Currency                         | `^[A-Z]{3}$`                                                                     |
| Time zone                        | Must be a valid IANA zone                                                        |
| Vehicle year                     | 1886 ≤ year ≤ current year + 1                                                   |
| VIN                              | 5–32 upper-case alphanumerics; a 17-char VIN must not contain I, O or Q          |
| Mileage                          | Integer 0 – 2 000 000                                                            |
| New mileage reading              | Must be ≥ the reading just before its date and ≤ the reading just after (`MILEAGE_DECREASE`, override with `force: true`, editor+) |
| `current_mileage` on create      | ≥ `initial_mileage`                                                              |
| Money                            | Decimal ≥ 0, ≤ 9 999 999 999.99, max 2 decimals (unit price: 4)                  |
| Service / fill / install dates   | Not in the future (1 day tolerance for time zones)                               |
| Document dates                   | `expiration_date ≥ issue_date`; reminder offsets 0–365, max 10 values, unique    |
| Schedule                         | At least one of `interval_km`, `interval_months`; intervals > 0                  |
| Fuel liters                      | > 0 and ≤ 1 000                                                                  |
| Fuel price consistency           | When `liters`, `price_per_liter` and `total_price` are all given, `|liters × price − total| ≤ 0.05` |
| Tire rotation                    | Final mounted positions must be unique; only mounted tires can rotate            |
| Fuel fill-ups                    | Mileage must grow with the date across fill-ups                                  |
| Shares                           | Registered, active user; not the owner; once per vehicle                         |
| Attachment / note parent         | `entity_id` must be a record of the same vehicle                                 |
| Request body size                | ≤ `MAX_UPLOAD_SIZE` + 1 MiB, rejected before reading (`413`)                      |
| Uploads                          | ≤ `MAX_UPLOAD_SIZE`; PDF, JPEG, PNG, WebP or HEIC detected from content; extension consistent |
| Pagination                       | `page ≥ 1`, `1 ≤ limit ≤ 100`                                                     |
| Sorting                          | Whitelisted fields only, `-field` for descending                                 |

## 19. Error handling strategy

Every error uses the same envelope:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid fields.",
    "fields": { "mileage": "Input should be greater than or equal to 0" },
    "request_id": "01J9Z..."
  }
}
```

* Services raise typed `AppError` subclasses (`NotFoundError`, `ConflictError`,
  `ForbiddenError`, `BusinessRuleError`, …) — they never build HTTP responses.
* Global handlers map them to status codes and the envelope. FastAPI request
  validation errors are flattened into `fields` with dotted paths
  (`moves.0.to_position`).
* Integrity errors that escape the services (race conditions on unique
  constraints) become `409 CONFLICT`.
* Unhandled exceptions are logged with the stack trace and the request id, and
  return `500 INTERNAL_ERROR` with a generic message.

| HTTP | Code                         | When                                                   |
|------|------------------------------|--------------------------------------------------------|
| 400  | `BAD_REQUEST`                | Malformed request outside schema validation            |
| 405  | `METHOD_NOT_ALLOWED`         | Unsupported HTTP method on a path                      |
| 401  | `AUTHENTICATION_REQUIRED`    | Missing/invalid access token or revoked session        |
| 401  | `TOKEN_EXPIRED`              | Expired access token (refresh it)                      |
| 401  | `ACCOUNT_DISABLED`           | Login to a disabled account                            |
| 401  | `INVALID_CREDENTIALS`        | Wrong email or password                                |
| 401  | `INVALID_TOKEN`              | Bad refresh / reset token                              |
| 403  | `FORBIDDEN`                  | Authenticated but role too low                         |
| 404  | `NOT_FOUND`                  | Resource missing or not accessible                     |
| 409  | `CONFLICT`                   | Unique constraint, resource in use                     |
| 409  | `EMAIL_ALREADY_REGISTERED`   | Registration with an existing email                    |
| 409  | `EXPENSE_LINKED_TO_SOURCE`   | Editing a linked expense directly                      |
| 409  | `VIN_ALREADY_REGISTERED`     | Same VIN twice for one owner                           |
| 409  | `SCHEDULE_EXISTS`            | Second schedule for the same type on a vehicle         |
| 409  | `TYPE_IN_USE`                | Deleting a custom type used by records                 |
| 409  | `TIRE_POSITION_TAKEN`        | Mounting a tire on an occupied position                |
| 409  | `ALREADY_SHARED`             | Sharing twice with the same user                       |
| 413  | `PAYLOAD_TOO_LARGE`          | Upload over the limit                                  |
| 415  | `UNSUPPORTED_MEDIA_TYPE`     | File type not allowed                                  |
| 422  | `VALIDATION_ERROR`           | Schema validation failed                               |
| 422  | `MILEAGE_DECREASE`           | Mileage lower than a previous reading                  |
| 422  | `BUSINESS_RULE_VIOLATION`    | Other domain rule (e.g. duplicate tire positions)      |
| 429  | `RATE_LIMITED`               | Too many requests (`Retry-After` header)               |
| 500  | `INTERNAL_ERROR`             | Unexpected error                                       |
| 503  | `SERVICE_UNAVAILABLE`        | Database unreachable (health)                          |

Success envelope:

```json
{ "success": true, "data": { } }
{ "success": true, "data": [ ], "meta": { "page": 1, "limit": 20, "total": 150, "total_pages": 8 } }
```

`204 No Content` responses have no body.

## 27. Example requests and responses

### Register

```http
POST /api/v1/auth/register
Content-Type: application/json

{ "email": "amina@example.com", "password": "S3cure-pass", "first_name": "Amina",
  "last_name": "Benali", "preferred_language": "fr", "preferred_currency": "MAD" }
```

```json
201 Created
{
  "success": true,
  "data": {
    "user": { "id": "0192...", "email": "amina@example.com", "first_name": "Amina",
              "last_name": "Benali", "preferred_language": "fr", "preferred_currency": "MAD",
              "preferred_distance_unit": "km", "created_at": "2026-10-06T13:00:00Z", "...": "..." },
    "tokens": { "access_token": "eyJhbGciOi...", "refresh_token": "q2V0...", "token_type": "bearer",
                "expires_in": 900, "refresh_expires_in": 2592000 }
  }
}
```

### Create a vehicle

```http
POST /api/v1/vehicles
Authorization: Bearer eyJhbGciOi...

{ "brand": "Dacia", "model": "Logan", "year": 2019, "fuel_type": "diesel",
  "license_plate": "12345-A-6", "initial_mileage": 80000, "current_mileage": 80000 }
```

### Record an oil change

```http
POST /api/v1/vehicles/0192.../oil-changes

{ "service_date": "2026-10-01", "mileage": 90150, "cost": "450.00",
  "oil_brand": "Total", "oil_type": "synthetic", "oil_viscosity": "5W-30",
  "oil_quantity_liters": "4.80", "oil_filter_changed": true, "filter_brand": "Purflux" }
```

Effects in one transaction: maintenance record + oil details, linked expense
(450.00 maintenance), mileage history entry (source `maintenance`), oil change
schedule moved to 100 150 km / 2027-10-01, open oil change alerts resolved.

### Validation error

```http
POST /api/v1/vehicles/0192.../mileage
{ "mileage": 1200 }
```

```json
422 Unprocessable Entity
{
  "success": false,
  "error": {
    "code": "MILEAGE_DECREASE",
    "message": "The new reading (1200 km) is lower than a previous reading (90150 km on 2026-10-01).",
    "fields": { "mileage": "Must be greater than or equal to 90150." },
    "request_id": "0192..."
  }
}
```

### Paginated list

```http
GET /api/v1/vehicles/0192.../maintenance?page=1&limit=20&sort=-service_date&kind=repair
```

```json
{ "success": true,
  "data": [ { "id": "...", "title": "Alternator replacement", "kind": "repair", "cost": "2100.00", "...": "..." } ],
  "meta": { "page": 1, "limit": 20, "total": 3, "total_pages": 1 } }
```

### Vehicle dashboard (abridged)

```json
{ "success": true,
  "data": {
    "vehicle": { "id": "...", "display_name": "Family Logan", "current_mileage": 98400, "access_role": "owner" },
    "current_mileage": 98400,
    "health": { "score": 40, "level": "critical", "overdue_maintenance": 1, "due_maintenance": 1,
                "expired_documents": 1, "expiring_documents": 1, "worn_parts": 0 },
    "maintenance": { "overdue": [ { "maintenance_type": { "code": "brake_fluid" }, "status": "overdue", "overdue_days": 70 } ],
                     "upcoming": [ { "maintenance_type": { "code": "vehicle_inspection" }, "status": "due_soon", "remaining_days": 15 } ] },
    "documents": { "expired": [ { "title": "Road tax", "status": "expired" } ],
                   "expiring": [ { "title": "Car insurance", "days_until_expiration": 20 } ] },
    "worn_parts": [],
    "alerts": { "summary": { "open": 5, "unread": 5, "by_priority": { "critical": 2, "high": 1, "medium": 2 } }, "latest": [ "..." ] },
    "recent_maintenance": [ "..." ], "recent_expenses": [ "..." ],
    "fuel": { "average_consumption_l_100km": 5.8, "last_consumption_l_100km": 5.6, "cost_per_km": 0.1043 },
    "costs": { "currency": "EUR", "total": "6930.20", "this_month": "8.00", "this_year": "1170.72",
               "total_maintenance_cost": "4410.00", "monthly": [ { "month": "2025-11", "total": "0.00" } ] }
  } }
```
