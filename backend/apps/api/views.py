from collections.abc import Iterable
from typing import Any

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from apps.api import serializers as s
from apps.api.authentication import ApiKeyAuthentication
from apps.api.models import ApiKey
from apps.api.throttles import AnonRateThrottle, ApiKeyRateThrottle, QuotaThrottle
from apps.api.usage import record
from apps.calendars.services import build_merged, visible_calendar
from apps.core import (
    MAX_YEAR,
    MIN_YEAR,
    Calendar,
    MergedCalendar,
    add_business_days,
    business_days_between,
    describe_days,
    get_calendar,
    holiday_sources,
    is_business_day,
    list_countries,
)

# A year has at least ~150 working days in every supported country, so this many extra years
# always covers an `add` walk.
WORKING_DAYS_PER_YEAR_FLOOR = 150


def _parse[T: s.CalendarQuerySerializer](serializer_class: type[T], request: Request) -> T:
    serializer = serializer_class(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer


def _calendar(request: Request, query: s.CalendarQuerySerializer, years: Iterable[int]) -> Calendar:
    calendar_id = query.validated_data.get("calendar")
    if calendar_id is not None:
        key_org = request.auth.org_id if isinstance(request.auth, ApiKey) else None
        return build_merged(visible_calendar(request.user, calendar_id, key_org), years)
    return get_calendar(years=years, **query.calendar_args())


def _holiday_entries(cal: Calendar) -> list[dict[str, Any]]:
    custom = cal.custom if isinstance(cal, MergedCalendar) else {}
    base = cal.holidays if isinstance(cal, MergedCalendar) else cal
    entries = []
    for day in base:
        closure = custom.get(day)
        for name in base.get_list(day):
            is_closure = closure is not None and closure.kind == "closure" and closure.name == name
            kind = "closure" if is_closure else "holiday"
            sources = [] if is_closure else list(holiday_sources(cal, day, name))
            entries.append({"date": day, "name": name, "kind": kind, "sources": sources})
    for day, item in custom.items():
        if item.kind == "half_day":
            entries.append({"date": day, "name": item.name, "kind": "half_day", "sources": []})
    return sorted(entries, key=lambda e: (e["date"], e["name"]))


class PublicView(APIView):
    authentication_classes = [ApiKeyAuthentication, SessionAuthentication]
    permission_classes = [AllowAny]
    throttle_classes = [
        AnonRateThrottle,
        UserRateThrottle,
        ScopedRateThrottle,
        ApiKeyRateThrottle,
        QuotaThrottle,
    ]

    def finalize_response(
        self, request: Request, response: Response, *args: Any, **kwargs: Any
    ) -> Response:
        response = super().finalize_response(request, response, *args, **kwargs)
        if isinstance(request.auth, ApiKey):
            endpoint = request.resolver_match.url_name if request.resolver_match else ""
            record(request.auth, endpoint or "", response.status_code, timezone.now())
        return response


class CountryListView(PublicView):
    @extend_schema(responses=s.CountrySerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response(s.CountrySerializer(list_countries().values(), many=True).data)


class HolidayListView(PublicView):
    @extend_schema(parameters=[s.HolidaysQuerySerializer], responses=s.HolidayListSerializer)
    def get(self, request: Request) -> Response:
        query = _parse(s.HolidaysQuerySerializer, request)
        year = query.validated_data["year"]
        cal = _calendar(request, query, [year])
        merged = isinstance(cal, MergedCalendar)
        base = cal.holidays if isinstance(cal, MergedCalendar) else cal
        payload = {
            "country": None if merged else base.country,
            "calendar": query.validated_data.get("calendar"),
            "subdiv": None if merged else base.subdiv,
            "year": year,
            "language": None if merged else base.language,
            "categories": [] if merged else sorted(base.categories),
            "holidays": _holiday_entries(cal),
        }
        return Response(s.HolidayListSerializer(payload).data)


class CheckView(PublicView):
    @extend_schema(parameters=[s.CheckQuerySerializer], responses=s.CheckResultSerializer)
    def get(self, request: Request) -> Response:
        query = _parse(s.CheckQuerySerializer, request)
        day = query.validated_data["date"]
        cal = _calendar(request, query, [day.year])
        return Response(s.CheckResultSerializer(is_business_day(cal, day)).data)


class AddView(PublicView):
    @extend_schema(parameters=[s.AddQuerySerializer], responses=s.AddResultSerializer)
    def get(self, request: Request) -> Response:
        query = _parse(s.AddQuerySerializer, request)
        start = query.validated_data["date"]
        days = query.validated_data["days"]
        reach = abs(days) // WORKING_DAYS_PER_YEAR_FLOOR + 1
        first = max(MIN_YEAR, start.year - reach if days < 0 else start.year)
        last = min(MAX_YEAR, start.year + reach if days >= 0 else start.year)
        cal = _calendar(request, query, range(first, last + 1))
        result = add_business_days(cal, start, days)
        return Response(
            s.AddResultSerializer({"start": start, "days": days, "result": result}).data
        )


class BetweenView(PublicView):
    @extend_schema(parameters=[s.BetweenQuerySerializer], responses=s.BetweenResultSerializer)
    def get(self, request: Request) -> Response:
        query = _parse(s.BetweenQuerySerializer, request)
        start = query.validated_data["start"]
        end = query.validated_data["end"]
        cal = _calendar(request, query, range(start.year, end.year + 1))
        count = business_days_between(cal, start, end)
        payload = {"start": start, "end": end, "business_days": count}
        return Response(s.BetweenResultSerializer(payload).data)


class RangeView(PublicView):
    @extend_schema(
        parameters=[s.RangeQuerySerializer], responses=s.CheckResultSerializer(many=True)
    )
    def get(self, request: Request) -> Response:
        query = _parse(s.RangeQuerySerializer, request)
        start = query.validated_data["start"]
        end = query.validated_data["end"]
        cal = _calendar(request, query, range(start.year, end.year + 1))
        return Response(s.CheckResultSerializer(describe_days(cal, start, end), many=True).data)
