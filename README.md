# Car Checker

Car Checker is a digital vehicle maintenance logbook. It tracks maintenance,
replaced parts, oil changes, tires, documents and their expiration dates,
mileage, expenses, fuel consumption, alerts and the full service history of
each vehicle.

This repository contains the **backend REST API**, the **database schema** and
the **web app**. The API is client-agnostic: the web app, and future Android,
desktop and mobile clients, all consume the same versioned API (`/api/v1`).

## Quick start (Docker)

```bash
docker compose up --build            # web app, API, worker, PostgreSQL, Redis
```

* Web app: <http://localhost:5173> (Vite dev server, `/api` proxied to the API)
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

The web app needs no local Node.js: it is developed, tested and built in Docker.

```bash
make fe-up          # web app on http://localhost:5173 (with the API)
make fe-check       # type check, lint, format check, unit tests
make fe-e2e         # Playwright end-to-end tests against the running stack
make fe-types       # regenerate the typed API client from the running API
make fe-build       # production image: static files served by nginx
docker compose --profile production up web   # production image on http://localhost:8080
```

## Deploy to Coolify

Use [`docker-compose.coolify.yml`](docker-compose.coolify.yml) for the production
web app, API, worker and Redis, with PostgreSQL as a separate Coolify database.
The [deployment guide](docs/09-deployment-coolify.md) covers GitHub access,
configuration, HTTPS, persistent uploads, verification and backups.

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
| `frontend/` | React + TypeScript web app, unit and end-to-end tests |
| `docs/`     | Architecture and design documentation               |

See [docs/README.md](docs/README.md) for the full design (stack, database,
security, API, domain rules, platform, plan).
