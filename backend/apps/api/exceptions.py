from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.api.errors import core_error_message
from apps.core import CoreError


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, CoreError):
        return Response({exc.field: [core_error_message(exc)]}, 400)
    return exception_handler(exc, context)
