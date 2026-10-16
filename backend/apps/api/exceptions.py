from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core import CoreError, YearNotCovered


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, YearNotCovered):
        return Response(
            {"non_field_errors": ["Result falls outside the supported year range."]}, 400
        )
    if isinstance(exc, CoreError):
        return Response({exc.field: [str(exc)]}, 400)
    return exception_handler(exc, context)
