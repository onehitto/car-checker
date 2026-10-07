# 28. Step-by-step backend implementation plan

Each step is one or more small commits, keeps the application runnable and is
covered by tests before moving on.

**Status:** phases 1 to 4 are implemented (see `git log`): 119 API operations,
26 tables, ~390 automated tests, ~98 % line coverage, strict mypy, Docker stack.
The "Later" list is the roadmap.

## Phase 1 — Foundation
1. Repository, documentation, Python project (`pyproject.toml`, Ruff, mypy, pytest).
2. Settings from environment variables with production safety checks.
3. Structured logging with redaction; request id middleware.
4. Response envelopes, `AppError` hierarchy and global error handlers.
5. Async database engine/session, declarative base, naming convention, UUIDv7, mixins.
6. Pagination and sorting helpers; clock abstraction.
7. Application factory: CORS, security headers, rate limiting, health endpoints.
8. Alembic environment; test infrastructure (test DB, transactional fixtures, client).

## Phase 2 — MVP
9. **Auth & users**: users, sessions, refresh tokens, reset tokens, audit log;
   register/login/refresh/logout/logout-all; password forgot/reset/change; profile,
   sessions, account deletion; email sender abstraction.
10. **Vehicles**: model + CRUD, vehicle role resolution and guards (sharing-ready).
11. **Mileage**: history, monotonic validation, current mileage maintenance.
12. **Garages**: CRUD (referenced by maintenance and parts).
13. **Maintenance types** + seed command; **maintenance records** CRUD with filters.
14. **Maintenance schedules** + calculator (status, remaining/overdue values) and
    record → schedule integration.
15. **Part types** + seed; **part replacements** with lifetime status.
16. **Documents** + expiration status logic.
17. **Expenses** CRUD + linked expenses for maintenance and parts.
18. **Alerts**: model, endpoints, i18n catalog, alert engine (schedules, documents,
    parts, stale mileage), engine hooks in services.
19. **Background jobs**: registry, advisory locks, scheduler, worker, CLI, jobs.
20. **Timeline** endpoint (UNION query with filters and pagination).
21. **Dashboard** (vehicle + global) with health score.

## Phase 3 — Complete feature set
22. Fuel records + consumption calculator + linked expenses + fuel statistics.
23. Statistics endpoints (by month/year/category, cost per km, frequency, top repairs).
24. Oil changes (maintenance extension).
25. Tires + events + rotations.
26. Attachments (validation, local storage backend, download, vehicle image).
27. Notes.
28. Vehicle sharing endpoints.
29. Custom reminders.
30. Notification preferences + delivery outbox + email channel + dispatch job.

## Phase 4 — Delivery
31. Dockerfile, entrypoint, docker-compose (api, worker, db, redis), `.env.example`.
32. Demo seed data, Makefile, README quick start.
33. Documentation pass: keep this folder in sync with the code.

## Later (not in scope of v1)
* S3 storage backend and pre-signed URLs.
* Offline sync endpoint + tombstones.
* Email verification, 2FA, OAuth providers.
* Push notifications (FCM/APNs) and SMS providers.
* VIN decoding, manufacturer maintenance plans, OBD-II ingestion, predictive maintenance.
* Fleet/organization accounts, mechanic accounts, resale history report, QR profile.
