# 17–18, 20–21, 24–25. Platform: files, jobs, Docker, configuration, docs, tests

## 17. File upload architecture

```
client ──multipart──▶ router ──▶ AttachmentService ──▶ validate ──▶ StorageBackend.save()
                                        │                               (local | s3)
                                        └──▶ INSERT attachments (metadata)
```

* **Generic attachments**: one `attachments` table, scoped to a vehicle, pointing
  to its parent with `entity_type` + `entity_id`. The service checks that the
  parent exists *on the same vehicle* before accepting the upload.
* **Validation** (`attachments/validation.py`):
  1. The request body is read in chunks; reading stops with `413` as soon as
     `MAX_UPLOAD_SIZE` is exceeded (no unbounded memory use).
  2. The real type is detected from magic bytes (`filetype`), never trusted from
     the client's `Content-Type`.
  3. Allowed types: `application/pdf`, `image/jpeg`, `image/png`, `image/webp`,
     `image/heic`. The file extension must match the detected type.
  4. The original file name is sanitized (path components, control characters and
     unsafe characters removed, length capped) and kept only as metadata.
* **Storage keys** are generated server-side:
  `{vehicle_id}/{yyyy}/{mm}/{uuid}.{ext}` — no user input ever reaches the file
  system path.
* **StorageBackend** interface: `save(key, data)`, `open(key)`, `delete(key)`.
  `LocalStorageBackend` writes under `UPLOAD_DIRECTORY` (a Docker volume, outside
  the application directory). An S3-compatible backend (AWS S3, MinIO, Backblaze,
  Scaleway…) implements the same interface; `attachments.storage_backend` records
  where each file lives, so a migration can move files progressively.
* **Downloads** go through the API (authorization check), with
  `Content-Disposition: attachment`, the stored content type and `nosniff`.
  With S3 the API can later return short-lived pre-signed URLs instead.
* **Deletion**: rows are deleted in the transaction; files are deleted after the
  commit. Deleting a vehicle removes its rows by cascade and the service deletes
  the files of that vehicle. A periodic `cleanup_orphan_files` job is the safety
  net for files whose row no longer exists.
* The vehicle picture is an attachment (`entity_type = vehicle`) referenced by
  `vehicles.image_attachment_id`.

## 18. Background job architecture

```
app/jobs/
├── registry.py   # @job("name") decorator → JOB_REGISTRY
├── tasks.py      # job functions: async def fn(ctx: JobContext) -> None
├── locks.py      # pg_try_advisory_lock helpers
└── scheduler.py  # APScheduler wiring (interval/cron triggers)
app/worker.py     # process entrypoint
app/cli.py        # python -m app.cli run-job <name>
```

| Job                         | Schedule      | Purpose                                                         |
|-----------------------------|---------------|-----------------------------------------------------------------|
| `generate_alerts`           | hourly        | Maintenance, documents, parts, reminders, stale mileage → alerts |
| `dispatch_notifications`    | every minute  | Send pending email/push/SMS deliveries                          |
| `cleanup_expired_tokens`    | daily 03:00   | Delete expired refresh/reset tokens and old revoked sessions     |
| `cleanup_orphan_files`      | daily 04:00   | Remove stored files without metadata rows                       |

Design rules:

* A job is a plain `async def` receiving a `JobContext` (session factory,
  settings, logger). It knows nothing about APScheduler — moving to arq/Celery
  means enqueuing the same functions.
* Each run takes a PostgreSQL **advisory lock** named after the job; if another
  worker holds it, the run is skipped. Safe with several worker replicas.
* Jobs process vehicles in batches and commit per batch, so a failure only rolls
  back one batch. Failures are logged with `job`, `duration_ms` and the exception;
  the scheduler keeps running.
* The API never runs the scheduler; only the `worker` process does.
* `python -m app.cli run-job generate_alerts` runs a job once (cron, debugging).

## 20. Docker architecture

```
docker-compose.yml
├── db       postgres:17-alpine   volume pgdata, healthcheck, init script creates car_checker_test
├── redis    redis:7-alpine       rate-limit counters (optional; memory backend without it)
├── api      build ./backend      entrypoint: migrate → seed → uvicorn (port 8000)
└── worker   same image           python -m app.worker
```

* **Dockerfile** (multi-stage): `builder` installs dependencies into a virtualenv;
  `runtime` copies the virtualenv and the code onto `python:3.12-slim`, runs as an
  unprivileged `app` user, exposes 8000 and declares a `HEALTHCHECK` on `/health`.
* `docker/entrypoint.sh` waits for the database, runs `alembic upgrade head` and
  `python -m app.cli seed` when `RUN_MIGRATIONS=true`, then `exec`s the command.
* Uploads live in a named volume mounted at `/data/uploads`.
* Start everything: `docker compose up --build`. API at <http://localhost:8000>,
  Swagger UI at <http://localhost:8000/docs>.
* Production: same image; point `DATABASE_URL` to the managed/remote database,
  set real secrets, `APP_ENV=production`, put a TLS reverse proxy in front.

## 21. Environment variables

| Variable                       | Default (dev)                                   | Description                                        |
|--------------------------------|-------------------------------------------------|----------------------------------------------------|
| `APP_ENV`                      | `development`                                   | `development`, `test`, `production`                |
| `API_PORT`                     | `8000`                                          | Port uvicorn listens on                            |
| `DATABASE_URL`                 | `postgresql+asyncpg://car_checker:car_checker@localhost:5432/car_checker` | Local or remote PostgreSQL |
| `TEST_DATABASE_URL`            | `…/car_checker_test`                            | Separate database used by the test suite           |
| `DATABASE_POOL_SIZE`           | `10`                                            | SQLAlchemy pool size                               |
| `JWT_SECRET`                   | dev placeholder (refused in production)         | Access token signing key (≥ 32 chars)              |
| `JWT_REFRESH_SECRET`           | dev placeholder (refused in production)         | HMAC key for refresh/reset token hashes            |
| `JWT_ISSUER` / `JWT_AUDIENCE`  | `car-checker` / `car-checker-clients`           | Token claims                                       |
| `ACCESS_TOKEN_EXPIRES_IN`      | `900`                                           | Seconds                                            |
| `REFRESH_TOKEN_EXPIRES_IN`     | `2592000`                                       | Seconds (30 days)                                  |
| `PASSWORD_RESET_EXPIRES_IN`    | `1800`                                          | Seconds                                            |
| `CORS_ORIGINS`                 | `http://localhost:3000,http://localhost:5173`   | Comma-separated list                               |
| `UPLOAD_DIRECTORY`             | `./var/uploads`                                 | Local storage root                                 |
| `MAX_UPLOAD_SIZE`              | `10485760`                                      | Bytes (10 MiB)                                     |
| `STORAGE_BACKEND`              | `local`                                         | `local` (S3 later)                                 |
| `REDIS_URL`                    | empty                                           | Enables the Redis rate-limit backend               |
| `RATE_LIMIT_ENABLED`           | `true`                                          |                                                    |
| `RATE_LIMIT_DEFAULT`           | `300/minute`                                    | Global per-client limit                            |
| `LOG_LEVEL` / `LOG_FORMAT`     | `INFO` / `console`                              | `json` in production                               |
| `ENABLE_DOCS`                  | `true` in development                           | Swagger UI, ReDoc, `/openapi.json`                 |
| `EMAIL_BACKEND`                | `console`                                       | `console`, `smtp`, `memory`                        |
| `EMAIL_FROM`                   | `Car Checker <no-reply@carchecker.local>`       |                                                    |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_STARTTLS` | — | SMTP provider                   |
| `FRONTEND_URL`                 | `http://localhost:3000`                         | Used to build password-reset links                 |
| `RUN_MIGRATIONS`               | `true` (compose)                                | Entrypoint migrates + seeds                        |
| `FORWARDED_ALLOW_IPS`          | `127.0.0.1`                                     | Trusted reverse proxies for client IPs             |

`backend/.env.example` lists them all. `.env` files are git-ignored. In
production, startup fails if secrets are missing, shorter than 32 characters or
equal to the development placeholders.

## 24. Swagger / OpenAPI setup

* FastAPI generates OpenAPI 3.1 from routers and Pydantic schemas.
* `/docs` (Swagger UI), `/redoc` and `/openapi.json` are enabled when
  `ENABLE_DOCS=true` (default only in development).
* A global `HTTPBearer` security scheme: the "Authorize" button accepts an access
  token; protected operations show the lock icon.
* Every router declares its common error responses (`401`, `403`, `404`, `409`,
  `422`, `429`) with the `ErrorResponse` schema, and success responses use the
  generic `ApiResponse[T]` / `PaginatedResponse[T]` envelopes, so the documented
  shapes are exactly what clients receive.
* Operations have tags per module, summaries and descriptions; enums are
  documented as string enums.
* Client SDKs (TypeScript, Kotlin, Dart) can be generated from `/openapi.json`
  with `openapi-generator`.

## 25. Testing strategy

| Level        | Scope                                                              | Tooling                       |
|--------------|--------------------------------------------------------------------|-------------------------------|
| Unit         | Calculators (maintenance due, document status, fuel consumption, units, month arithmetic), validators, security helpers | pytest, no DB |
| Integration  | HTTP endpoints through the real app and a real PostgreSQL database | pytest-asyncio, httpx `ASGITransport` |
| Security     | Authentication flows, token rotation/reuse, authorization matrix (owner/editor/viewer/stranger) | integration |
| Jobs         | Alert generation, notification dispatch, token cleanup             | integration, job functions called directly |

* **Separate database**: `TEST_DATABASE_URL` (`car_checker_test`). The schema is
  created once per test session with the Alembic migrations.
* **Isolation**: each test runs inside an outer transaction that is rolled back;
  service commits become savepoints (`join_transaction_mode="create_savepoint"`).
  Tests are independent and fast.
* **Determinism**: "today" is injected (`Clock` dependency), so date-based tests
  do not depend on the calendar.
* Run: `docker compose up -d db && cd backend && pytest` (or `make test`).
* Coverage report: `pytest --cov=app --cov-report=term-missing`.
