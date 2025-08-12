from .base import *  # noqa

# Allow toggling via env: DJANGO_DEBUG=true/false
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

# Apply secure settings when not in debug
if not DEBUG:
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")


