from datetime import date, datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDate

from apps.api.models import ApiKey, UsageEvent
from apps.orgs.models import Organization

LAST_USED_PRECISION = timedelta(minutes=1)
RETENTION = timedelta(days=90)


def plan_limits(org: Organization) -> dict[str, Any]:
    return settings.PLANS[org.plan]


def quota_key(org_id: int, now: datetime) -> str:
    return f"quota:{org_id}:{now:%Y%m}"


def used_this_month(org: Organization, now: datetime) -> int:
    value: int = cache.get(quota_key(org.pk, now), 0)
    return value


def seconds_until_next_month(now: datetime) -> int:
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    following = (first + timedelta(days=32)).replace(day=1)
    return max(1, int((following - now).total_seconds()))


def mark_used(api_key: ApiKey, now: datetime) -> None:
    if api_key.last_used_at is None or now - api_key.last_used_at > LAST_USED_PRECISION:
        ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=now)


def record(api_key: ApiKey, endpoint: str, status: int, now: datetime) -> None:
    UsageEvent.objects.create(
        org_id=api_key.org_id, api_key=api_key, endpoint=endpoint[:60], status=status
    )
    if status != 429:
        key = quota_key(api_key.org_id, now)
        # add() sets the counter only if it's missing; 32 days outlives the month it counts.
        cache.add(key, 0, timeout=32 * 24 * 3600)
        cache.incr(key)


def daily_counts(org: Organization, today: date, days: int) -> list[dict[str, Any]]:
    first = today - timedelta(days=days - 1)
    rows = (
        UsageEvent.objects.filter(org=org, created_at__date__gte=first)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(requests=Count("id"), failed=Count("id", filter=Q(status__gte=400)))
    )
    by_day = {row["day"]: (row["requests"], row["failed"]) for row in rows}
    result = []
    for n in range(days):
        day = first + timedelta(days=n)
        requests, failed = by_day.get(day, (0, 0))
        result.append({"date": day, "requests": requests, "failed": failed})
    return result
