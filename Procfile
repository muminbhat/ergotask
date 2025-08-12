web: gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A backend worker -l info --concurrency=1
beat: celery -A backend beat -l info


