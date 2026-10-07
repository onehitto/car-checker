# Car Checker — backend

FastAPI + PostgreSQL REST API for the Car Checker vehicle maintenance logbook.
Design documentation lives in [`../docs`](../docs/README.md).

## Requirements

* Python 3.12
* PostgreSQL 17 (`docker compose up -d db` from the repository root)
* Redis (optional, shared rate-limit counters)

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env                       # adjust if needed
.venv/bin/alembic upgrade head             # schema
.venv/bin/python -m app.cli seed           # system catalogs (idempotent)
.venv/bin/python -m app.cli seed --demo    # optional demo account
```

## Run

```bash
.venv/bin/uvicorn app.main:create_app --factory --reload   # API on :8000, docs on /docs
.venv/bin/python -m app.worker                              # scheduled jobs
.venv/bin/python -m app.cli list-jobs                       # registered jobs
.venv/bin/python -m app.cli run-job generate_alerts         # run one job now
```

## Quality

```bash
.venv/bin/pytest                    # needs the car_checker_test database
.venv/bin/pytest --cov=app          # coverage report
.venv/bin/ruff check app tests && .venv/bin/ruff format --check app tests
.venv/bin/mypy app                  # strict
```

## Migrations

```bash
.venv/bin/alembic revision --autogenerate -m "describe the change"   # then review it
.venv/bin/alembic upgrade head
.venv/bin/alembic upgrade head --sql > schema.sql                      # full DDL
```

Check constraints (enum values) are not detected by autogenerate: write those
changes by hand. A test fails if the migrations and the models drift apart.
