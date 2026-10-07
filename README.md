# Car Checker

Car Checker is a digital vehicle maintenance logbook. It tracks maintenance,
replaced parts, oil changes, tires, documents and their expiration dates,
mileage, expenses, fuel consumption, alerts and the full service history of
each vehicle.

This repository contains the **backend REST API** and the **database schema**.
The API is client-agnostic: web, Android, desktop and future mobile clients all
consume the same versioned API (`/api/v1`).

## Quick start (Docker)

```bash
docker compose up --build            # API, worker, PostgreSQL, Redis
```

* Swagger UI: <http://localhost:8000/docs> (ReDoc: `/redoc`, schema: `/openapi.json`)
* Health: <http://localhost:8000/health>
* Optional demo data: `docker compose exec api python -m app.cli seed --demo`, then
  sign in with `demo@example.com` / `Car-checker-2026`.

The API container applies migrations and reference data on start
(`RUN_MIGRATIONS=true`); the worker runs the scheduled jobs (alerts,
notifications, cleanups).

## Local development

```bash
make install        # virtualenv + dependencies (Python 3.12)
make infra          # PostgreSQL + Redis in Docker
make migrate seed   # schema + system catalogs
make run            # API with auto-reload on http://localhost:8000
make worker         # background jobs (optional)
make check          # ruff + strict mypy + tests (separate test database)
```

`make help` lists every target. Configuration comes from environment variables,
see [`backend/.env.example`](backend/.env.example).

## What is inside

| Area            | Highlights                                                                 |
|-----------------|----------------------------------------------------------------------------|
| Auth & users    | Argon2id, JWT access tokens + rotating refresh tokens with reuse detection, sessions, password reset/change, account deletion |
| Vehicles        | Owner / editor / viewer roles, sharing, odometer history with monotonic validation, vehicle picture |
| Maintenance     | Records and repairs, oil changes, schedules by km and/or months with `ok → upcoming → due soon → due → overdue` status |
| Parts & tires   | Part replacements with expected lifetime, tire positions, rotations and history |
| Documents       | Insurance, registration, inspection... with configurable reminder steps |
| Alerts          | Idempotent alert engine, translated (en/fr/ar), in-app inbox, e-mail outbox (push/SMS ready) |
| Money & fuel    | Single expense ledger with linked expenses, full-tank fuel consumption, statistics per vehicle and currency |
| Views           | Vehicle and user dashboards with health score, chronological timeline |
| Platform        | Attachments (magic-byte validation, pluggable storage), notes, jobs with advisory locks, rate limiting, structured logs, OpenAPI |

## Repository layout

| Path        | Content                                             |
|-------------|-----------------------------------------------------|
| `backend/`  | FastAPI application, migrations, tests              |
| `docs/`     | Architecture and design documentation               |

See [docs/README.md](docs/README.md) for the full design (stack, database,
security, API, domain rules, platform, plan).
