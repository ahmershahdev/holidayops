"""Working-day overlap: which days in a month are working days in every chosen country."""

from dataclasses import dataclass
from datetime import date, timedelta

from django.utils.translation import gettext as _

from apps.core import CountryInfo, get_calendar, is_business_day, list_countries
from apps.public.content import country_name, holiday_language, year_window

MAX_COUNTRIES = 4
DEFAULT = ("PK", "SA", "GB")


@dataclass(frozen=True)
class Off:
    code: str
    name: str
    reason: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class OverlapDay:
    day: date | None
    off: tuple[Off, ...] = ()
    kind: str = "pad"


@dataclass(frozen=True)
class Overlap:
    month: date
    # (code, name, working days in the month) per country.
    countries: tuple[tuple[str, str, int], ...]
    weeks: tuple[tuple[OverlapDay, ...], ...]
    shared: int
    partial: int
    closed: int


def parse(codes: list[str], month: str, today: date) -> tuple[list[str], date, str]:
    """Validated countries and month, plus an error message ("" if none)."""
    known = list_countries()
    chosen = list(dict.fromkeys(c.upper()[:3] for c in codes if c))[:MAX_COUNTRIES]
    try:
        first = date.fromisoformat(f"{month[:7]}-01") if month else today.replace(day=1)
    except ValueError:
        return list(DEFAULT), today.replace(day=1), _("Pick a valid month.")
    if first.year not in year_window(today):
        return chosen or list(DEFAULT), today.replace(day=1), _("Pick a month within five years.")
    if not chosen:
        return list(DEFAULT), first, ""
    if any(c not in known for c in chosen):
        return (
            [c for c in chosen if c in known] or list(DEFAULT),
            first,
            _("Pick countries from the list."),
        )
    if len(chosen) < 2:
        return chosen, first, _("Pick at least two countries to compare.")
    return chosen, first, ""


def _language(info: CountryInfo, lang: str) -> str | None:
    return holiday_language(info, lang) or holiday_language(info, "en")


def overlap(codes: list[str], first: date, lang: str) -> Overlap:
    infos = [list_countries()[c] for c in codes]
    calendars = [get_calendar(i.code, None, [first.year], _language(i, lang), ()) for i in infos]
    names = {i.code: country_name(i.code, lang) for i in infos}
    days: list[OverlapDay] = [OverlapDay(None)] * first.weekday()
    working = dict.fromkeys(codes, 0)
    shared = partial = closed = 0
    day = first
    while day.month == first.month:
        off = []
        for info, cal in zip(infos, calendars, strict=True):
            result = is_business_day(cal, day)
            if result.is_business_day:
                working[info.code] += 1
            else:
                off.append(Off(info.code, names[info.code], result.reason, result.holidays))
        if not off:
            kind, shared = "shared", shared + 1
        elif len(off) == len(infos):
            kind, closed = "closed", closed + 1
        else:
            kind, partial = "partial", partial + 1
        days.append(OverlapDay(day, tuple(off), kind))
        day += timedelta(days=1)
    days += [OverlapDay(None)] * (-len(days) % 7)
    weeks = tuple(tuple(days[i : i + 7]) for i in range(0, len(days), 7))
    countries = tuple((code, names[code], working[code]) for code in codes)
    return Overlap(first, countries, weeks, shared, partial, closed)
