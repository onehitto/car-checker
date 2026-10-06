# syntax=docker/dockerfile:1.7
# Car Checker backend image: one image for the API and the background worker.

ARG PYTHON_VERSION=3.12

# --- Build stage: dependencies in a virtualenv --------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build

# Dependencies first (cached until pyproject.toml changes)...
COPY pyproject.toml README.md ./
RUN mkdir app && touch app/__init__.py \
    && pip install . \
    && pip uninstall -y car-checker-backend

# ...then the application package itself.
COPY app ./app
RUN pip install --no-deps .

# --- Runtime stage --------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    API_PORT=8000 \
    UPLOAD_DIRECTORY=/data/uploads \
    LOG_FORMAT=json

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /srv/app --shell /usr/sbin/nologin app \
    && mkdir -p /data/uploads \
    && chown app:app /data/uploads

WORKDIR /srv/app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY --chmod=0755 docker/entrypoint.sh /usr/local/bin/entrypoint.sh

USER app
EXPOSE 8000
VOLUME ["/data/uploads"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('API_PORT', '8000') + '/health', timeout=4)"

ENTRYPOINT ["entrypoint.sh"]
CMD ["api"]
