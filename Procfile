web: bash bin/start.sh
worker: celery -A backend worker -l info --concurrency=1
beat: celery -A backend beat -l info


