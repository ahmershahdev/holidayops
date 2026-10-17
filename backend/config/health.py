from collections.abc import Callable

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache

PROBE_KEY = "healthz"
PATH = "/healthz"


class HealthCheckMiddleware:
    """Answers /healthz before host validation and the HTTPS redirect: load balancer probes
    call the container by IP over plain HTTP. Keep it first in MIDDLEWARE."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path == PATH:
            return healthz(request)
        return self.get_response(request)


@never_cache
def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness and readiness in one: 200 when the database and the cache answer, else 503."""
    checks = {"database": _database(), "cache": _cache()}
    healthy = all(checks.values())
    return JsonResponse(
        {
            "status": "ok" if healthy else "error",
            **{k: "ok" if v else "error" for k, v in checks.items()},
        },
        status=200 if healthy else 503,
    )


def _database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return bool(cursor.fetchone() == (1,))
    except Exception:
        return False


def _cache() -> bool:
    try:
        cache.set(PROBE_KEY, "1", timeout=10)
        return bool(cache.get(PROBE_KEY) == "1")
    except Exception:
        return False
