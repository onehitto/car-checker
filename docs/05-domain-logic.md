# 13–16. Domain logic

All calculations are pure functions (no database access) that receive `today`
and `current_mileage` explicitly. "Today" is evaluated in the user's time zone
(`users.timezone`).

## 13. Maintenance calculation logic

Implemented in `app/modules/maintenance/calculator.py`.

### Next service

```
next_service_mileage = last_service_mileage + interval_km
next_service_date    = last_service_date + interval_months   (calendar months,
                                                               day clamped: Jan 31 + 1 month = Feb 28/29)
```

Resolution order for each dimension:

1. `last_service_*` known → computed from the interval.
2. Otherwise an explicit `next_service_*` given by the user (e.g. the first
   service from the manufacturer's booklet) is kept.
3. Otherwise the vehicle baseline is used: `initial_mileage` and `purchase_date`
   (or the vehicle creation date) — a car bought at 80 000 km with an unknown oil
   history gets its first oil change due at 90 000 km.

`next_service_*` are persisted on the schedule (indexed, so the alert job can
scan them) and recomputed whenever the schedule changes or a matching
maintenance record is saved.

Saving a maintenance record whose type has a schedule on the same vehicle moves
the schedule forward when the record is the most recent service
(`last_service_date/mileage` ← record, `next_*` recomputed) — in the same
transaction.

### Status

For each dimension (km, days) with remaining value `r` and warning window `w`:

```
remaining_km   = next_service_mileage - current_mileage
remaining_days = next_service_date - today

r < 0                      → OVERDUE
r ≤ min(due_window, w)     → DUE          due_window = 300 km / 7 days
r ≤ w                      → DUE_SOON
r ≤ 2·w                    → UPCOMING
otherwise                  → OK
```

The schedule status is the **most severe** of the two dimensions ("whichever
comes first"). When neither dimension can be computed the status is `UNKNOWN`.
Disabled schedules report `OK` with no alert.

Returned values: `next_service_date`, `next_service_mileage`, `remaining_km`,
`remaining_days`, `overdue_km = max(0, -remaining_km)`,
`overdue_days = max(0, -remaining_days)`, `status`, `due_reason`
(`mileage`, `date` or `both`).

Example — oil change every 10 000 km / 12 months, last done 2025-11-01 at
50 000 km, warnings 1 000 km / 30 days, today 2026-10-06, odometer 59 400 km:

| Dimension | Next         | Remaining | Window test        | Result    |
|-----------|--------------|-----------|--------------------|-----------|
| km        | 60 000       | 600       | 300 < 600 ≤ 1000   | DUE_SOON  |
| days      | 2026-11-01   | 26        | 7 < 26 ≤ 30        | DUE_SOON  |

→ status `due_soon`.

### Parts lifetime

Same function with `installed_date/installed_mileage` as the last service,
`expected_lifetime_km/months` as intervals and fixed warnings of 1 000 km / 30
days. Only parts that have not been removed are evaluated. Installing a new part
of the same type and position marks the previous one as removed.

### Vehicle health score

```
score = 100
      − 25 per overdue schedule      − 10 per due schedule      − 5 per due-soon schedule
      − 25 per expired document      − 5 per expiring-soon document
      − 10 per overdue part          − 5 per due / due-soon part
clamped to [0, 100]
```

`80–100 good`, `50–79 attention`, `< 50 critical`.

## 14. Alert generation logic

Implemented in `app/modules/alerts/engine.py`. The engine is **idempotent** and
runs:

* synchronously for one vehicle after writes that change deadlines (mileage,
  maintenance records, schedules, parts, documents, reminders), inside the same
  transaction, so the API is immediately consistent;
* periodically for every vehicle by the worker (`generate_alerts` job, hourly),
  because time passes without writes.

For each **source** (schedule, document, part, reminder, vehicle mileage) the
engine computes the *desired* alert (or none):

| Source                  | Condition                                    | alert_type             | Priority mapping |
|-------------------------|----------------------------------------------|------------------------|------------------|
| Maintenance schedule    | status ≥ UPCOMING                            | `maintenance_due` (`inspection_due` for the inspection type) | upcoming → low, due_soon → medium, due → high, overdue → critical |
| Vehicle document        | a reminder offset reached or expired         | `insurance_expiration`, `inspection_due` (technical inspection) or `document_expiration` | > 30 d → low, ≤ 30 d → medium, ≤ 7 d → high, expired → critical |
| Part replacement        | lifetime status ≥ DUE_SOON                   | `part_lifetime`        | as maintenance   |
| Reminder                | status ≥ DUE_SOON and not completed          | `custom_reminder`      | as maintenance   |
| Vehicle mileage         | last reading older than 30 days (active vehicles) | `mileage_reminder` | info             |

Each desired alert has a **dedup key** describing the source, the deadline and
the severity, e.g. `maintenance_schedule:{id}:2026-11-01:60000:due_soon`.

Reconciliation per source and recipient:

1. Open alerts (`active`/`read`) of the source whose key differs from the desired
   key are set to `resolved` (`resolved_at = now`) — the situation changed
   (service done, document renewed, severity escalated).
2. If a desired alert exists and no alert with that key exists for the
   recipient (in any status), it is inserted. A user who *dismissed* an alert is
   not bothered again with the same key, but is notified again on escalation.
3. If there is no desired alert, every open alert of the source is resolved.

Recipients are the vehicle owner and editors. Viewers (e.g. a buyer or a
mechanic) do not receive alerts.

Titles and messages are rendered with the translation catalog in the
recipient's `preferred_language` (`en`, `fr`, `ar`). `template_key` and
`template_params` are stored too, so clients can render them in another
language.

### Notifications

When an alert is created, a `notification_deliveries` row is inserted for each
external channel enabled for the recipient and the alert priority
(`notification_preferences`; defaults: in-app all, email ≥ high, push/sms off).
The in-app channel *is* the alerts table. The `dispatch_notifications` job
(every minute) sends pending deliveries through channel providers:

| Channel | Provider (v1)                                  |
|---------|------------------------------------------------|
| email   | SMTP / console / in-memory (tests)             |
| push    | not configured → delivery marked `skipped`     |
| sms     | not configured → delivery marked `skipped`     |

Failures are retried up to 5 times, then marked `failed`.

## 15. Document expiration logic

Implemented in `app/modules/documents/expiration.py`.

```
days_left = expiration_date − today

no expiration date              → VALID
days_left < 0                   → EXPIRED
days_left ≤ max(reminder_days)  → EXPIRING_SOON     (default reminder_days = [30, 7, 1, 0])
otherwise                       → VALID
```

The "expiring soon" window follows the user's own reminder configuration: a
document configured with `[90, 30, 15, 7, 1, 0]` becomes *expiring soon* 90
days before expiration.

Reminder selection: the active reminder offset is the smallest configured
offset `o` with `o ≥ days_left`. The dedup key contains it, so the user receives
one alert per reminder step (90 → 30 → 15 → 7 → 1 → 0 → expired), each one
resolving the previous. Changing the expiration date (renewal) resolves all
alerts of the old period.

## 16. Expense and fuel calculation logic

### Expenses

* Expenses are the single money ledger (see linked expenses in the database
  design). All amounts of a vehicle are in `vehicles.currency`; cross-vehicle
  statistics are grouped by currency.
* Totals and groupings are computed in SQL (`SUM`, `date_trunc`, `GROUP BY`).
* `average_monthly_cost = total / number of months in the period`, where the
  period is the requested range or, by default, from the first expense to today.
* `cost_per_km = total / distance driven in the period`; distance =
  max(mileage) − min(mileage) across mileage readings of the period.

### Fuel (full-tank method)

Fill-ups are ordered by mileage. For each **full** fill-up `F` whose previous
full fill-up is `P`, with no `missed_previous` flag in between:

```
liters_used  = Σ liters of fill-ups after P up to and including F (partials included)
distance     = F.mileage − P.mileage
consumption  = liters_used / distance × 100            (L/100 km)
```

Per fill-up the API returns `distance_since_previous` (always, when a previous
fill-up exists) and `consumption_l_100km` (only when computable).

Aggregates:

| Value                     | Formula                                                     |
|---------------------------|-------------------------------------------------------------|
| average consumption       | Σ liters_used / Σ distance × 100 over computable segments (distance-weighted, not an average of averages) |
| fuel cost per km          | Σ total_price / Σ distance over the same segments           |
| monthly fuel spending     | Σ total_price grouped by month of `fill_date`               |
| total liters, total cost  | Σ over the period                                           |

Unit conversions (`app/core/units.py`):

```
km/L      = 100 / (L/100km)
MPG (US)  = 235.214583 / (L/100km)
MPG (UK)  = 282.480936 / (L/100km)
miles     = km × 0.621371
```

Statistics endpoints accept `distance_unit` and `consumption_unit` query
parameters (defaulting to the user's preferences) and return converted values;
records are always stored and returned in km and litres.
