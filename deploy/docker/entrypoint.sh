#!/bin/sh
# ══════════════════════════════════════════════════════════════════
# NOCTRA container entrypoint
#
#   1. optionally wait for PostgreSQL
#   2. optionally apply Alembic migrations
#   3. optionally seed reference data
#   4. exec the container command (uvicorn by default)
#
# Every step is opt-out so the same image works for one-shot jobs
# (e.g. `docker compose run --rm app python -m scripts.create_superuser`)
# without touching the database.
# ══════════════════════════════════════════════════════════════════
set -eu

log() {
    printf '%s [entrypoint] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    log "waiting for PostgreSQL at ${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}"
    python -m scripts.wait_for_db

    log "applying migrations (alembic upgrade head)"
    alembic -c /app/alembic.ini upgrade head
fi

if [ "${RUN_SEED:-0}" = "1" ]; then
    log "seeding reference data"
    python -m scripts.seed_all
fi

if [ "${RUN_SUPERUSER:-0}" = "1" ]; then
    log "creating superuser (interactive)"
    python -m scripts.create_superuser
fi

exec "$@"
