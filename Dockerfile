# syntax=docker/dockerfile:1.7
# ══════════════════════════════════════════════════════════════════
# NOCTRA — production image
#
#   docker build -t noctra .
#   docker compose --env-file .env.docker up -d --build
#
# The image contains the application, migrations, and operational
# scripts. Configuration and secrets are supplied at runtime through
# environment variables (see .env.docker.example); nothing secret is
# baked in.
# ══════════════════════════════════════════════════════════════════

FROM python:3.13-slim AS deps
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PORT=8000

# Unprivileged runtime user. The media directory is owned by it so the
# named volume initialises with the right permissions.
RUN groupadd --system --gid 10001 noctra \
 && useradd --system --uid 10001 --gid noctra \
        --home-dir /app --shell /usr/sbin/nologin noctra \
 && mkdir -p /app/media \
 && chown -R noctra:noctra /app

WORKDIR /app

COPY --from=deps /opt/venv /opt/venv
COPY --chown=noctra:noctra app ./app
COPY --chown=noctra:noctra alembic ./alembic
COPY --chown=noctra:noctra alembic.ini ./
COPY --chown=noctra:noctra scripts ./scripts
COPY --chown=noctra:noctra deploy/docker/entrypoint.sh \
     /usr/local/bin/noctra-entrypoint
RUN chmod 0555 /usr/local/bin/noctra-entrypoint

USER noctra
EXPOSE 8000

# Liveness only — the container should not restart just because the
# database is briefly unavailable. `/readyz` is for orchestrators.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"

# The entrypoint optionally waits for PostgreSQL and applies migrations
# before exec'ing this command. Keep one worker by default: the overdue
# sweep scheduler and rate limiter are per-process.
ENTRYPOINT ["/usr/local/bin/noctra-entrypoint"]
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*", \
     "--no-server-header"]
