"""Backend project package initializer.

Keeps `DJANGO_SETTINGS_MODULE=backend.settings` working by exposing the default
settings module via the `backend.settings` package which imports from
`backend.settings.base`. Environment-specific settings can be selected via
`DJANGO_SETTINGS_MODULE=backend.settings.dev` or `backend.settings.prod`.
Also exposes Celery app for autodiscovery.
"""

from .celery import app as celery_app  # noqa: F401


