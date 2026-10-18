"""'Is today a working day?' per country, in that country's own time zone. Docs: docs/seo.md."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache
from zoneinfo import ZoneInfo

from babel.core import get_global
from django.core.cache import cache as django_cache
from django.utils import timezone

from apps.core import (
    Calendar,
    CountryInfo,
    add_business_days,
    get_calendar,
    is_business_day,
    list_countries,
)
from apps.public.content import PREFIX, country_name, holiday_language, page_path

# CLDR lists a country's zones alphabetically ("America/Adak" first for the US), so countries
# spanning zones use their capital's. Territories with no CLDR zone fall back to UTC.
CAPITAL_ZONES = {
    "AU": "Australia/Sydney",
    "BR": "America/Sao_Paulo",
    "CA": "America/Toronto",
    "CD": "Africa/Kinshasa",
    "CL": "America/Santiago",
    "CY": "Asia/Nicosia",
    "EC": "America/Guayaquil",
    "ES": "Europe/Madrid",
    "FM": "Pacific/Pohnpei",
    "GL": "America/Nuuk",
    "ID": "Asia/Jakarta",
    "KI": "Pacific/Tarawa",
    "KZ": "Asia/Almaty",
    "MH": "Pacific/Majuro",
    "MN": "Asia/Ulaanbaatar",
    "MX": "America/Mexico_City",
    "MY": "Asia/Kuala_Lumpur",
    "PF": "Pacific/Tahiti",
    "PG": "Pacific/Port_Moresby",
    "PS": "Asia/Hebron",
    "PT": "Europe/Lisbon",
    "RU": "Europe/Moscow",
    "UA": "Europe/Kyiv",
    "UM": "Pacific/Wake",
    "US": "America/New_York",
    "UZ": "Asia/Tashkent",
    "XK": "Europe/Belgrade",
}
LOOKAHEAD_DAYS = 400
WEEK = 7


@cache
def country_zone(code: str) -> ZoneInfo:
    zones = get_global("territory_zones").get(code) or ["UTC"]
    return ZoneInfo(CAPITAL_ZONES.get(code, zones[0]))


def local_today(code: str, now: datetime | None = None) -> date:
    return (now or timezone.now()).astimezone(country_zone(code)).date()


@dataclass(frozen=True)
class DayStatus:
    day: date
    working: bool
    reason: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class CountryToday:
    code: str
    name: str
    path: str
    zone: str
    today: DayStatus
    week: tuple[DayStatus, ...]
    next_holiday: DayStatus | None
    next_working: date


def _status(cal: Calendar, day: date) -> DayStatus:
    result = is_business_day(cal, day)
    return DayStatus(day, result.is_business_day, result.reason, result.holidays)


def _language(info: CountryInfo, lang: str) -> str | None:
    return holiday_language(info, lang) or holiday_language(info, "en")


def country_today(info: CountryInfo, lang: str, today: date) -> CountryToday:
    years = [today.year, (today + timedelta(days=LOOKAHEAD_DAYS)).year]
    cal = get_calendar(info.code, None, sorted(set(years)), _language(info, lang), ())
    upcoming = sorted(d for d in cal if today < d <= today + timedelta(days=LOOKAHEAD_DAYS))
    return CountryToday(
        code=info.code,
        name=country_name(info.code, lang),
        path=page_path(lang, info.code, today.year),
        zone=country_zone(info.code).key,
        today=_status(cal, today),
        week=tuple(_status(cal, today + timedelta(days=n)) for n in range(WEEK)),
        next_holiday=_status(cal, upcoming[0]) if upcoming else None,
        # days=0 is today when it's a working day, otherwise the next one.
        next_working=add_business_days(cal, today + timedelta(days=1), 0),
    )


@dataclass(frozen=True)
class Row:
    code: str
    name: str
    path: str
    status: DayStatus


@dataclass(frozen=True)
class WorldToday:
    holiday: tuple[Row, ...]
    weekend: tuple[Row, ...]
    working: tuple[Row, ...]


def world_today(lang: str, now: datetime | None = None) -> WorldToday:
    """Every country on its own local date, cached for the hour: somewhere a new day starts
    every hour."""
    now = now or timezone.now()
    key = f"today:{now:%Y%m%d%H}:{lang}"
    cached: WorldToday | None = django_cache.get(key)
    if cached is not None:
        return cached
    rows = []
    for code, info in list_countries().items():
        day = local_today(code, now)
        cal = get_calendar(code, None, [day.year], _language(info, lang), ())
        rows.append(Row(code, country_name(code, lang), today_path(lang, code), _status(cal, day)))
    rows.sort(key=lambda row: row.name)
    result = WorldToday(
        holiday=tuple(r for r in rows if r.status.names),
        weekend=tuple(r for r in rows if not r.status.names and r.status.reason == "weekend"),
        working=tuple(r for r in rows if not r.status.names and r.status.working),
    )
    django_cache.set(key, result, 3600)
    return result


def today_path(lang: str, code: str) -> str:
    return f"{PREFIX[lang]}/holidays/{code.lower()}/today/"
