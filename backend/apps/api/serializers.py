from datetime import date
from typing import Any, get_args

from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.core import MAX_YEAR, MIN_YEAR, Reason

MAX_ADD_DAYS = 1000
MAX_BETWEEN_SPAN_DAYS = 3660
MAX_RANGE_DAYS = 366
REASONS = list(get_args(Reason))


def validate_supported_year(value: date) -> None:
    if not MIN_YEAR <= value.year <= MAX_YEAR:
        raise serializers.ValidationError(
            _("Year must be between %(min)s and %(max)s.") % {"min": MIN_YEAR, "max": MAX_YEAR}
        )


class CalendarQuerySerializer(serializers.Serializer[Any]):
    country = serializers.CharField(
        required=False, max_length=3, help_text="ISO 3166-1 alpha-2 code, e.g. PK."
    )
    calendar = serializers.UUIDField(
        required=False, help_text="A company calendar id, instead of country."
    )
    subdiv = serializers.CharField(required=False, allow_blank=True, max_length=10)
    language = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=10,
        help_text="Defaults to the country's language.",
    )
    categories = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        help_text="Comma-separated. Default: public.",
    )

    def validate_subdiv(self, value: str) -> str | None:
        return value or None

    def validate_language(self, value: str) -> str | None:
        return value or None

    def validate_categories(self, value: str) -> tuple[str, ...]:
        return tuple(item.strip() for item in value.split(",") if item.strip())

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        if ("country" in attrs) == ("calendar" in attrs):
            raise serializers.ValidationError(
                {"country": [_("Give exactly one of country or calendar.")]}
            )
        if "calendar" in attrs:
            given = [f for f in ("subdiv", "language", "categories") if attrs.get(f)]
            if given:
                raise serializers.ValidationError(
                    {given[0]: [_("Not allowed with calendar; the calendar defines it.")]}
                )
        return attrs

    def calendar_args(self) -> dict[str, Any]:
        data = self.validated_data
        return {
            "country": data["country"],
            "subdiv": data.get("subdiv"),
            "language": data.get("language"),
            "categories": data.get("categories", ()),
        }


class HolidaysQuerySerializer(CalendarQuerySerializer):
    year = serializers.IntegerField(min_value=MIN_YEAR, max_value=MAX_YEAR)


class CheckQuerySerializer(CalendarQuerySerializer):
    date = serializers.DateField(validators=[validate_supported_year])


class AddQuerySerializer(CalendarQuerySerializer):
    date = serializers.DateField(validators=[validate_supported_year])
    days = serializers.IntegerField(min_value=-MAX_ADD_DAYS, max_value=MAX_ADD_DAYS)


class BetweenQuerySerializer(CalendarQuerySerializer):
    start = serializers.DateField(validators=[validate_supported_year])
    end = serializers.DateField(validators=[validate_supported_year])

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        span = (attrs["end"] - attrs["start"]).days
        if span < 0:
            raise serializers.ValidationError({"end": [_("End must not be before start.")]})
        if span > MAX_BETWEEN_SPAN_DAYS:
            raise serializers.ValidationError(
                {
                    "end": [
                        _("Range must not exceed %(days)s days.") % {"days": MAX_BETWEEN_SPAN_DAYS}
                    ]
                }
            )
        return attrs


class RangeQuerySerializer(CalendarQuerySerializer):
    start = serializers.DateField(validators=[validate_supported_year])
    end = serializers.DateField(validators=[validate_supported_year])

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        span = (attrs["end"] - attrs["start"]).days
        if not 0 <= span < MAX_RANGE_DAYS:
            raise serializers.ValidationError(
                {
                    "end": [
                        _("End must be on or after start and within %(days)s days.")
                        % {"days": MAX_RANGE_DAYS}
                    ]
                }
            )
        return attrs


class CountrySerializer(serializers.Serializer[Any]):
    code = serializers.CharField()
    name = serializers.CharField()
    subdivisions = serializers.ListField(child=serializers.CharField())
    languages = serializers.ListField(child=serializers.CharField())
    default_language = serializers.CharField(allow_null=True)
    categories = serializers.ListField(child=serializers.CharField())
    weekend = serializers.ListField(
        child=serializers.IntegerField(), help_text="Weekday numbers, Monday = 0."
    )


class HolidaySerializer(serializers.Serializer[Any]):
    date = serializers.DateField()
    name = serializers.CharField()
    kind = serializers.ChoiceField(choices=["holiday", "closure", "half_day"])
    sources = serializers.ListField(
        child=serializers.CharField(),
        help_text="Source countries (with subdivision) that contribute this holiday.",
    )


class HolidayListSerializer(serializers.Serializer[Any]):
    country = serializers.CharField(allow_null=True)
    calendar = serializers.UUIDField(allow_null=True)
    subdiv = serializers.CharField(allow_null=True)
    year = serializers.IntegerField()
    language = serializers.CharField(allow_null=True)
    categories = serializers.ListField(child=serializers.CharField())
    holidays = HolidaySerializer(many=True)


class CheckResultSerializer(serializers.Serializer[Any]):
    date = serializers.DateField(source="day")
    is_business_day = serializers.BooleanField()
    reason = serializers.ChoiceField(choices=REASONS)
    holidays = serializers.ListField(child=serializers.CharField())
    half_day = serializers.BooleanField()


class AddResultSerializer(serializers.Serializer[Any]):
    start = serializers.DateField()
    days = serializers.IntegerField()
    result = serializers.DateField()


class BetweenResultSerializer(serializers.Serializer[Any]):
    start = serializers.DateField()
    end = serializers.DateField()
    business_days = serializers.IntegerField(help_text="Inclusive of both start and end.")
