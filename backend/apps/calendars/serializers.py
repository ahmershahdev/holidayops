from typing import Any

from django.db import transaction
from rest_framework import serializers

from apps.api.serializers import validate_supported_year
from apps.calendars.models import Calendar, CalendarSource, CustomDay
from apps.core import CoreError, check_calendar_args, get_country

MAX_SOURCES = 20


class SourceSerializer(serializers.ModelSerializer[CalendarSource]):
    categories = serializers.ListField(
        child=serializers.CharField(max_length=30), required=False, max_length=10
    )

    class Meta:
        model = CalendarSource
        fields = ["country", "subdiv", "categories"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs["country"] = attrs["country"].upper()
        attrs["categories"] = sorted(set(attrs.get("categories", [])))
        try:
            check_calendar_args(
                attrs["country"], attrs.get("subdiv") or None, None, attrs["categories"]
            )
        except CoreError as exc:
            raise serializers.ValidationError({exc.field: [str(exc)]}) from exc
        return attrs


class CalendarSerializer(serializers.ModelSerializer[Calendar]):
    sources = SourceSerializer(many=True)
    weekend = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        allow_null=True,
        required=False,
        max_length=6,
        help_text="Weekday numbers (Monday = 0). Null uses the first source's weekend.",
    )

    class Meta:
        model = Calendar
        fields = [
            "id",
            "name",
            "slug",
            "is_public",
            "language",
            "weekend",
            "sources",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def validate_sources(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not 1 <= len(value) <= MAX_SOURCES:
            raise serializers.ValidationError(f"Give between 1 and {MAX_SOURCES} sources.")
        return value

    def validate_weekend(self, value: list[int] | None) -> list[int] | None:
        if value is not None and len(set(value)) != len(value):
            raise serializers.ValidationError("Weekdays must not repeat.")
        return sorted(value) if value is not None else None

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        language = attrs.get("language", self.instance.language if self.instance else "")
        if "sources" in attrs:
            countries = [source["country"] for source in attrs["sources"]]
        elif self.instance is not None:
            countries = [source.country for source in self.instance.sources.all()]
        else:
            countries = []
        if language and not any(language in get_country(c).languages for c in countries):
            raise serializers.ValidationError(
                {"language": ["No source country supports this language."]}
            )
        return attrs

    def _save_sources(self, calendar: Calendar, sources: list[dict[str, Any]]) -> None:
        calendar.sources.all().delete()
        CalendarSource.objects.bulk_create(
            CalendarSource(calendar=calendar, position=i, **source)
            for i, source in enumerate(sources)
        )

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Calendar:
        sources = validated_data.pop("sources")
        calendar = Calendar.objects.create(**validated_data)
        self._save_sources(calendar, sources)
        return calendar

    @transaction.atomic
    def update(self, instance: Calendar, validated_data: dict[str, Any]) -> Calendar:
        sources = validated_data.pop("sources", None)
        calendar = super().update(instance, validated_data)
        if sources is not None:
            self._save_sources(calendar, sources)
        return calendar


class CustomDaySerializer(serializers.ModelSerializer[CustomDay]):
    date = serializers.DateField(validators=[validate_supported_year])

    class Meta:
        model = CustomDay
        fields = ["id", "date", "name", "kind"]

    def validate_date(self, value: Any) -> Any:
        calendar: Calendar = self.context["calendar"]
        taken = calendar.custom_days.filter(date=value)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError(
                "This calendar already has a custom day on this date."
            )
        return value
