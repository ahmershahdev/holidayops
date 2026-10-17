import logging
from typing import Any

from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.api.errors import core_error_message
from apps.core import CoreError
from config.security_log import security_event


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, CoreError):
        return Response({exc.field: [core_error_message(exc)]}, 400)
    if isinstance(exc, Throttled) and "request" in context:
        scope = getattr(context.get("view"), "throttle_scope", None) or "api"
        level = logging.WARNING if scope in ("auth", "invite") else logging.INFO
        security_event("rate_limited", context["request"], level, scope=scope)
    return exception_handler(exc, context)
