from typing import Any

from django.utils import timezone
from rest_framework import throttling
from rest_framework.request import Request

from apps.api.models import ApiKey
from apps.api.usage import plan_limits, seconds_until_next_month, used_this_month


class AnonRateThrottle(throttling.AnonRateThrottle):
    """Per-IP limit for anonymous calls; a request with an API key has its own limits."""

    def get_cache_key(self, request: Request, view: Any) -> str | None:
        if isinstance(request.auth, ApiKey):
            return None
        return super().get_cache_key(request, view)


class ApiKeyRateThrottle(throttling.SimpleRateThrottle):
    scope = "api_key"

    def allow_request(self, request: Request, view: Any) -> bool:
        if not isinstance(request.auth, ApiKey):
            return True
        self.rate = str(plan_limits(request.auth.org)["rate"])
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_rate(self) -> str | None:
        # The rate depends on the key's plan, so allow_request sets it per request.
        return None

    def get_cache_key(self, request: Request, view: Any) -> str | None:
        assert isinstance(request.auth, ApiKey)
        return self.cache_format % {"scope": self.scope, "ident": request.auth.prefix}


class QuotaThrottle(throttling.BaseThrottle):
    """Monthly requests per org. Only checks; usage.record counts the requests that got through."""

    def allow_request(self, request: Request, view: Any) -> bool:
        if not isinstance(request.auth, ApiKey):
            return True
        now = timezone.now()
        quota = int(plan_limits(request.auth.org)["monthly_quota"])
        if used_this_month(request.auth.org, now) < quota:
            return True
        self._wait = seconds_until_next_month(now)
        return False

    def wait(self) -> float | None:
        return self._wait
