Backend (Django REST Framework)

Quick start
1) Create virtualenv and install requirements:
   - pip install -r requirements.txt
2) Set environment:
   - copy .env.example to .env and adjust values (PostgreSQL or keep dev sqlite)
3) Run migrations and server:
   - python manage.py migrate
   - python manage.py runserver

API docs
- Swagger: /api/docs/
- ReDoc: /api/redoc/
- OpenAPI schema: /api/schema/

Apps
- catalog: categories
- contexts: daily context entries
- tasks: tasks CRUD and AI suggestion hook (placeholder)


