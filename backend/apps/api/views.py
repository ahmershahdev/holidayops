from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api import serializers as s
from apps.core import (
    MAX_YEAR,
    MIN_YEAR,
    add_business_days,
    business_days_between,
    get_calendar,
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


class CountryListView(APIView):
    @extend_schema(responses=s.CountrySerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response(s.CountrySerializer(list_countries().values(), many=True).data)


class HolidayListView(APIView):
    @extend_schema(parameters=[s.HolidaysQuerySerializer], responses=s.HolidayListSerializer)
    def get(self, request: Request) -> Response:
        query = _parse(s.HolidaysQuerySerializer, request)
        year = query.validated_data["year"]
        cal = get_calendar(years=[year], **query.calendar_args())
        items = sorted((day, name) for day in cal for name in cal.get_list(day))
        payload = {
            "country": cal.country,
            "subdiv": cal.subdiv,
            "year": year,
            "language": cal.language,
            "categories": sorted(cal.categories),
            "holidays": [{"date": day, "name": name} for day, name in items],
        }
        return Response(s.HolidayListSerializer(payload).data)


class CheckView(APIView):
    @extend_schema(parameters=[s.CheckQuerySerializer], responses=s.CheckResultSerializer)
    def get(self, request: Request) -> Response:
        query = _parse(s.CheckQuerySerializer, request)
        day = query.validated_data["date"]
        cal = get_calendar(years=[day.year], **query.calendar_args())
        return Response(s.CheckResultSerializer(is_business_day(cal, day)).data)


class AddView(APIView):
    @extend_schema(parameters=[s.AddQuerySerializer], responses=s.AddResultSerializer)
    def get(self, request: Request) -> Response:
        query = _parse(s.AddQuerySerializer, request)
        start = query.validated_data["date"]
        days = query.validated_data["days"]
        reach = abs(days) // WORKING_DAYS_PER_YEAR_FLOOR + 1
        first = max(MIN_YEAR, start.year - reach if days < 0 else start.year)
        last = min(MAX_YEAR, start.year + reach if days >= 0 else start.year)
        cal = get_calendar(years=range(first, last + 1), **query.calendar_args())
        result = add_business_days(cal, start, days)
        return Response(
            s.AddResultSerializer({"start": start, "days": days, "result": result}).data
        )


class BetweenView(APIView):
    @extend_schema(parameters=[s.BetweenQuerySerializer], responses=s.BetweenResultSerializer)
    def get(self, request: Request) -> Response:
        query = _parse(s.BetweenQuerySerializer, request)
        start = query.validated_data["start"]
        end = query.validated_data["end"]
        cal = get_calendar(years=range(start.year, end.year + 1), **query.calendar_args())
        count = business_days_between(cal, start, end)
        payload = {"start": start, "end": end, "business_days": count}
        return Response(s.BetweenResultSerializer(payload).data)
