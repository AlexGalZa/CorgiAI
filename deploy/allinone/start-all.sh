#!/bin/bash
set -e

if [ -n "${DATABASE_HOST:-}" ] && [ -n "${DATABASE_PORT:-}" ]; then
    echo "[corgi] Waiting for PostgreSQL at ${DATABASE_HOST}:${DATABASE_PORT}..."
    until pg_isready -h "${DATABASE_HOST}" -p "${DATABASE_PORT}" -U "${DATABASE_USER:-postgres}" -d "${DATABASE_NAME:-postgres}" >/dev/null 2>&1; do
        sleep 1
    done
    echo "[corgi] PostgreSQL ready"
fi

cd /app/api

echo "[corgi] Running migrations..."
python manage.py migrate --noinput

echo "[corgi] Collecting static files..."
python manage.py collectstatic --noinput || echo "[corgi] collectstatic skipped/failed (non-fatal)"

echo "[corgi] Starting supervisord..."
exec supervisord -n -c /etc/supervisor/supervisord.conf
