import uuid
from collections.abc import Iterable
from typing import Any

from django.db.models import Q
from django.http import Http404

from apps.calendars.models import Calendar
from apps.core import CustomDay, MergedCalendar, get_calendar, get_country, merge_calendars


def visible_calendar(user: Any, calendar_id: uuid.UUID, org_id: int | None = None) -> Calendar:
    """Public calendars, the user's orgs' calendars, and those of `org_id` (an API key's org)."""
    access = Q(is_public=True)
    if user is not None and user.is_authenticated:
        access |= Q(org__memberships__user=user)
    if org_id is not None:
        access |= Q(org_id=org_id)
    calendar = Calendar.objects.filter(access, id=calendar_id).distinct().first()
    if calendar is None:
        raise Http404
    return calendar


def _source_language(calendar: Calendar, country: str) -> str | None:
    if calendar.language and calendar.language in get_country(country).languages:
        return calendar.language
    return None


def build_merged(calendar: Calendar, years: Iterable[int]) -> MergedCalendar:
    year_list = list(years)
    sources = [
        get_calendar(
            source.country,
            source.subdiv or None,
            year_list,
            _source_language(calendar, source.country),
            tuple(source.categories),
        )
        for source in calendar.sources.all()
    ]
    custom = [
        CustomDay(day.date, day.name, day.kind)  # type: ignore[arg-type]
        for day in calendar.custom_days.filter(date__year__in=year_list)
    ]
    return merge_calendars(sources, custom, calendar.weekend)
