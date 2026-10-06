# Car Checker

Car Checker is a digital vehicle maintenance logbook. It tracks maintenance,
replaced parts, oil changes, tires, documents and their expiration dates,
mileage, expenses, fuel consumption, alerts and the full service history of
each vehicle.

This repository contains the **backend REST API** and the **database schema**.
The API is client-agnostic: web, Android, desktop and future mobile clients all
consume the same versioned API (`/api/v1`).

## Repository layout

| Path        | Content                                             |
|-------------|-----------------------------------------------------|
| `backend/`  | FastAPI application, migrations, tests              |
| `docs/`     | Architecture and design documentation               |

See [docs/README.md](docs/README.md) for the full design.
