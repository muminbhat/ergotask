from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def exception_handler(exc: Exception, context: dict[str, Any]):
    response = drf_exception_handler(exc, context)

    if response is not None:
        # Ensure consistent error shape
        response.data = {
            "error": {
                "type": exc.__class__.__name__,
                "detail": response.data,
                "status_code": response.status_code,
            }
        }
        return response

    # Unhandled errors
    logger.exception("Unhandled exception", extra={"view": context.get("view").__class__.__name__ if context.get("view") else None})
    from rest_framework.response import Response

    return Response(
        {"error": {"type": exc.__class__.__name__, "detail": str(exc), "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


