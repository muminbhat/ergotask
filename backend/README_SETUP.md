# Backend setup cheatsheet

## Install
- Python 3.11+
- pip install -r backend/requirements.txt

## Environment
- For dev (SQLite): default works via `backend.settings.dev`
- For Postgres: set `DB_*` env vars and use `backend.settings.prod`
- AI (optional): set `OPENAI_API_KEY` and `OPENAI_MODEL`
- Celery:
  - `CELERY_BROKER_URL=redis://localhost:6379/0`
  - `CELERY_TASK_ALWAYS_EAGER=true` to run tasks inline

## Run
- cd backend
- python manage.py migrate
- python manage.py seed_categories
- python manage.py seed_sample_data
- python manage.py runserver
- In another shell: `celery -A backend worker -l info`

## Docs
- /api/docs, /api/redoc, /api/schema

