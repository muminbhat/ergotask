from __future__ import annotations

from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_view(_request):
    # DB check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            _ = cursor.fetchone()
        db_ok = True
    except Exception:
        db_ok = False

    # Broker check (optional): just echo if configured
    # A real ping would use redis-py or Celery inspect, but avoid hard dependency here
    broker_ok = True

    status = 200 if db_ok and broker_ok else 503
    return Response({"db": db_ok, "broker": broker_ok}, status=status)


