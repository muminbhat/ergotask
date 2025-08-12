Smart Todo API (Backend) - Prepared for Ergosphere.io (Evaluation Purpose Only) - By Mumin Bhat (12th August 2025)

Overview
- AI-powered task management with context analysis, priority scoring, deadline suggestions, and scheduling.
- This service exposes a REST API that is used by the Next.js frontend.


- Can be accessed here: **https://ergotask.muminbhat.com/**

- Below are the screenshots that are attached from the Frontend

- Dashboard
   
<img width="1896" height="1079" alt="Screenshot 2025-08-12 172139" src="https://github.com/user-attachments/assets/6f3b48c3-afdf-4997-9350-69272b3e7f8b" />

- Tasks

<img width="1918" height="1079" alt="Screenshot 2025-08-12 172154" src="https://github.com/user-attachments/assets/5463b3f4-9571-4ec3-b6cb-0bfa41200414" />

- Context

<img width="1919" height="1074" alt="Screenshot 2025-08-12 172208" src="https://github.com/user-attachments/assets/f641e85b-efc2-4813-842c-79580ebbd5ca" />

- Task Detail

<img width="1919" height="1079" alt="Screenshot 2025-08-12 172230" src="https://github.com/user-attachments/assets/9952b262-c08e-42c8-bb32-79b9e417f15d" />

Local setup

1) Python 3.11+ and virtualenv or venv as you preffer
2) Install deps:
   - `pip install -r requirements.txt`
3) Run with SQLite (dev): Please set these environment variables in order for application to work.
   - `DJANGO_SETTINGS_MODULE=backend.settings.dev`
   - `DJANGO_ALLOWED_HOSTS=endpoint.com`
   - `FRONTEND_ORIGIN=https://ergotask.muminbhat.com`
   - `DJANGO_DEBUG=false`
   - `REDIS_URL=...`
   - `python manage.py migrate`
   - `python manage.py seed_categories` (This will populate some data in db)
   - `python manage.py runserver`
4) Run with PostgreSQL (Prod):
   - Set env:
     - `DJANGO_SETTINGS_MODULE=backend.settings.prod`
     - `DATABASE_URL=postgresql://<user>:<pass>@<host>:<port>/<db>`
     - `FRONTEND_ORIGIN=https://frontend-endpoint`
     - FOR AI TO WORK:
       - `AI_PROVIDER=openai`
       - `OPENAI_API_KEY=...`
   - `python manage.py migrate && python manage.py seed_categories && python manage.py runserver`

Key API endpoints
- Auth (JWT):
  - `POST /api/auth/token/`
  - `POST /api/auth/token/refresh/`
  - `POST /api/auth/register/`
- Tasks:
  - `GET /api/v1/tasks/` list/search/filter
  - `POST /api/v1/tasks/` create
  - `PATCH /api/v1/tasks/{id}/` update
  - `DELETE /api/v1/tasks/{id}/` delete
  - `POST /api/v1/tasks/{id}/ai-suggestions/` see suggestions
  - `POST /api/v1/tasks/{id}/ai-apply/` apply suggestions
  - `POST /api/v1/tasks/{id}/schedule-suggestions/` schedule suggestions
  - `POST /api/v1/tasks/nl-create/` (create from free text)
  - `POST /api/v1/tasks/seed-sample-data/` (seed sample data for current user)
- Contexts:
  - `GET /api/v1/contexts/`
  - `POST /api/v1/contexts/`
- Categories:
  - `GET /api/v1/categories/`
- Docs: `/api/docs/`, `/api/redoc/`, `/api/schema/`

AI behavior
- Providers: OpenAI
- Orchestrator returns priority score, deadline, enhanced description, categories, and reasoning.
- NL date parsing: robust to natural phrases (e.g., "tomorrow", "next Tuesday", "after 3 days").


