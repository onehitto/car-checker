# Deploy Car Checker to Coolify

Use the repository's [`docker-compose.coolify.yml`](../docker-compose.coolify.yml)
for production. Keep the development stack in `docker-compose.yml` for local
work. Deploy the production file on its own; do not merge it with the development
Compose file. The production stack builds the existing application Dockerfiles.

| Resource | Role | Public access | Persistent data |
|----------|------|---------------|-----------------|
| `web` | Built React app served by nginx; proxies `/api/` and `/health` | One HTTPS domain, internal port `8080` | None |
| `api` | FastAPI, migrations and reference-data seed | Through `web` | Shared uploads at `/data/uploads` |
| `worker` | Alerts, notification delivery and cleanup jobs | None | Same uploads volume |
| `redis` | Shared rate-limit counters | None | Counters can be recreated |
| Separate PostgreSQL 17 resource | Application database | Private destination network | Coolify database volume |

The frontend uses the current website's origin for API requests. A second API
domain or frontend API build variable is unnecessary. Deploy one API container
initially: it migrates and seeds the database before starting, and the worker
starts after the API becomes healthy. Reference data is seeded idempotently;
demo accounts are never created in production. The worker runs the scheduler,
so its inherited API HTTP health check is disabled.

## 1. Connect GitHub

In Coolify **Sources**, create a GitHub App source and use automated installation
while signed in as **onehitto**. Grant access to the selected repository
**onehitto/car-checker**. The app supports deployments from pushes to the selected
branch; its webhook endpoint must be reachable by GitHub.
[Coolify GitHub App setup](https://coolify.io/docs/applications/sources/github/app)

## 2. Create PostgreSQL

Create a standalone PostgreSQL resource in the target project/environment,
using the same server and destination network as the application. Explicitly
choose **`postgres:17-alpine`** and set the initial database to **`car_checker`**;
Coolify's current default major version may differ. Review the generated
credentials, start the database, and wait until it is healthy. Keep public TCP
access disabled.
[Coolify PostgreSQL setup](https://coolify.io/docs/databases/postgresql)

Copy the database's **internal** connection URL. For this application, replace
its `postgres://` or `postgresql://` scheme with `postgresql+asyncpg://`:

```text
postgresql+asyncpg://USER:PASSWORD@INTERNAL_DATABASE_HOST:5432/car_checker
```

Keep the generated internal hostname, credentials and database name. Do not
use `localhost` or the development hostname `db`. Percent-encode reserved
characters in a username or password when constructing a connection URL.

## 3. Create the application

Create a Git-based application from **onehitto/car-checker**, with:

| Setting | Value |
|---------|-------|
| Branch | `main` |
| Build strategy / build pack | Docker Compose |
| Base directory | `/` |
| Docker Compose location | `/docker-compose.coolify.yml` |
| Connect to predefined network | Enabled; same destination as PostgreSQL |
| Raw Compose deployment | Disabled |

Save and load the Compose definition. Coolify manages the proxy routing and
resource networking; `web` reaches `api:8000` inside the stack, and the backend
reaches PostgreSQL through the predefined destination network.
[Coolify Docker Compose setup](https://coolify.io/docs/applications/builds/docker-compose)

## 4. Set production configuration

Enter secrets in the application's **Environment Variables**, with runtime
availability enabled. The Compose file passes configuration explicitly into
both backend containers; an arbitrary new Coolify variable is not automatically
application configuration unless it is referenced by the Compose definition.

For the initial deployment without email, use these values, replacing every
example. Database, both JWT secrets, frontend URL and trusted proxy CIDR are
required; CORS defaults to the frontend URL.

```dotenv
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@INTERNAL_DATABASE_HOST:5432/car_checker
JWT_SECRET=REPLACE_WITH_A_RANDOM_ACCESS_TOKEN_SECRET
JWT_REFRESH_SECRET=REPLACE_WITH_A_DIFFERENT_RANDOM_REFRESH_TOKEN_SECRET
FRONTEND_URL=https://cars.example.com
CORS_ORIGINS=https://cars.example.com
TRUSTED_PROXY_CIDR=REPLACE_WITH_VERIFIED_PROXY_CIDR
EMAIL_BACKEND=console
```

Generate each JWT secret separately:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Use two different values of at least 32 characters, and retain them between
deployments. Changing them invalidates existing sessions. `FRONTEND_URL` is the
public origin, without `:8080` or a trailing slash, because it is used in
password-reset links. `CORS_ORIGINS` accepts comma-separated allowed origins;
it defaults to `FRONTEND_URL` when unset. Use the same HTTPS origin and never `*`.

`TRUSTED_PROXY_CIDR` is required for nginx. Set it to the Coolify reverse
proxy's actual source address (`/32` for IPv4, `/128` for IPv6) or the verified
Docker subnet containing that proxy. It accepts one CIDR. Find the container
and its network addresses on the **deployment server**:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}'
docker inspect PROXY_CONTAINER_NAME --format '{{json .NetworkSettings.Networks}}'
docker network inspect NETWORK_NAME --format '{{json .IPAM.Config}}'
```

Replace the uppercase names with the proxy container and network found in the
output. Choose the network through which the proxy connects to `web`. A verified
destination-network subnet can be used before the first deployment; if Coolify
routes through a generated application network instead, inspect the deployed
`web` container's networks and update the CIDR before the final smoke checks.
Trusting a subnet also trusts its other containers, so use a dedicated trusted
network. Do not use `0.0.0.0/0`, `::/0`, or an unverified example address.

FastAPI separately needs to trust its immediate nginx peer.
`FORWARDED_ALLOW_IPS` defaults to the private IPv4 ranges
`10.0.0.0/8,172.16.0.0/12,192.168.0.0/16` for dynamic Docker addresses. For
tighter isolation, override it with the specific application subnet or nginx
address; include the matching IPv6 range if your Docker network uses IPv6.

The production Compose file fixes `APP_ENV=production`, `LOG_FORMAT=json`,
`STORAGE_BACKEND=local`, `UPLOAD_DIRECTORY=/data/uploads` and
the private Redis connection. It keeps migrations enabled only on `api`.
`LOG_LEVEL` defaults to `INFO` and can be overridden. Swagger and OpenAPI are
disabled by the application's production default.

`EMAIL_BACKEND` defaults to `console`, allowing the API and worker to start
without SMTP settings. **Password-reset emails and email notifications are
unavailable in this mode.** In production, the console backend withholds email
content instead of printing messages or reset links. `EMAIL_FROM` is optional
and defaults to `Car Checker <no-reply@carchecker.local>`.

To enable email later, add this configuration in Coolify and redeploy:

```dotenv
EMAIL_BACKEND=smtp
EMAIL_FROM=Car Checker <no-reply@example.com>
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=REPLACE_WITH_YOUR_SMTP_USERNAME
SMTP_PASSWORD=REPLACE_WITH_YOUR_SMTP_PASSWORD
SMTP_STARTTLS=true
```

SMTP mode requires `SMTP_HOST` before the API can start. Use your provider's
approved sender address and STARTTLS settings, typically port `587`. The current
sender supports SMTP with STARTTLS; implicit SMTPS on port `465` is not
implemented. Set both credentials for an authenticated provider; a trusted
relay can leave them empty. The API sends password-reset email, and the worker
dispatches notification email.

Do not commit real `.env` files or place credentials in frontend build arguments.

To validate configuration locally, save the settings in an ignored
`.env.coolify` file at the repository root and run:

```bash
docker compose --env-file .env.coolify -f docker-compose.coolify.yml config --quiet
```

This validates interpolation without printing secret values or starting
containers. The production file is used on its own, without the development
Compose file.

## 5. Assign HTTPS and deploy

Point the domain's DNS records at the Coolify server. Assign
**`https://cars.example.com:8080`** to service **`web`**, then deploy. Coolify uses
`8080` as the container destination; visitors open **`https://cars.example.com`**.
The Compose services do not publish host ports. Wait for API migrations to
finish and for `web`, `api` and `redis` to become healthy.
[Coolify Compose domain configuration](https://coolify.io/docs/applications/builds/docker-compose#configure-public-services)

The request path is HTTPS → Coolify proxy → nginx → FastAPI. nginx accepts the
original scheme and client-address chain only from `TRUSTED_PROXY_CIDR`, then
forwards the resolved client address to FastAPI. This preserves HTTPS context
and lets API rate limits identify clients correctly.

## 6. Verify the deployment

1. Open the HTTPS domain and refresh a nested page to check SPA routing.
2. Check the health endpoint:

   ```bash
   curl --fail https://cars.example.com/health
   ```

   The response should contain `data.status=ok` and `data.database=ok`.
3. Register an account, sign in, create a vehicle, and upload/download an
   attachment. Redeploy and confirm that the attachment remains available.
4. With `EMAIL_BACKEND=smtp`, request a password reset; verify email delivery
   and that the link uses the public HTTPS origin. Check worker logs for
   `worker_started` and subsequent successful scheduled jobs. Notification
   delivery runs every minute; email is disabled with `EMAIL_BACKEND=console`.
5. Inspect logs for database, Redis or SMTP errors and confirm client addresses
   are preserved when requests reach API rate limits.

`/health` verifies API and database connectivity; it does not verify SMTP,
Redis or worker job execution. Check those operations separately. In Coolify,
health checks come from the Compose definition and images, including the
disabled HTTP check on the worker.

## 7. Back up and maintain the deployment

* Schedule PostgreSQL backups for `car_checker` and enable upload to validated
  S3-compatible storage outside the deployment server. Configure local and S3
  retention independently, and inspect backup executions. Read the schedule's
  displayed timezone before choosing a cron time.
  [Coolify database backups](https://coolify.io/docs/databases/backups)
* Back up the **uploads volume** separately to off-server storage. Find its
  actual Coolify-managed name in Persistent Storage; both backend containers
  use this one volume. A database backup contains attachment metadata, not
  file contents. For a coordinated recovery point, stop application writes
  while taking database and uploads backups.
  [Coolify volume mounts and backups](https://coolify.io/docs/core/persistent-storage/storage-mounts/volume-mounts)
* Test restoration into a separate database and uploads volume, then verify
  login, vehicles and attachment downloads. Restore both data sets together
  and preserve the image/commit and configuration needed to read them.
* Keep one API deployment during migrations. Back up before schema changes;
  selecting an older application commit does not reverse database migrations.
  Persistent uploads currently assume one deployment server; moving servers
  requires copying the volume, and object-storage support is future work.
* Keep preview deployments off until they have a separate database, secrets,
  upload volume and frontend origin. A preview must not migrate or clean up
  the production data.

For later releases, push the reviewed commit to `main` and deploy that commit
through Coolify. Enable automatic deployments when the initial smoke checks
and backup restoration succeed.
