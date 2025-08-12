#!/usr/bin/env sh
set -euo pipefail

export PYTHONUNBUFFERED=1

echo "[start] Collecting static files"
python manage.py collectstatic --noinput || true

echo "[start] Making migrations (safe if none)"
python manage.py makemigrations --noinput || true

echo "[start] Applying migrations"
python manage.py migrate --noinput

echo "[start] Seeding categories (idempotent)"
python manage.py seed_categories || true

echo "[start] Launching gunicorn"
exec gunicorn backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}


