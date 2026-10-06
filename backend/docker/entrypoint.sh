#!/bin/sh
# Container entrypoint.
#   api     -> (optional) migrations + seed, then the HTTP API
#   worker  -> background job scheduler
#   *       -> any other command (e.g. `python -m app.cli run-job generate_alerts`)
set -eu

python -m app.cli wait-db --timeout "${DB_WAIT_TIMEOUT:-60}"

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    alembic upgrade head
    python -m app.cli seed
fi

case "${1:-api}" in
    api)
        exec uvicorn app.main:create_app --factory \
            --host 0.0.0.0 \
            --port "${API_PORT:-8000}" \
            --workers "${WEB_CONCURRENCY:-1}" \
            --proxy-headers \
            --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
            --no-server-header
        ;;
    worker)
        exec python -m app.worker
        ;;
    *)
        exec "$@"
        ;;
esac
