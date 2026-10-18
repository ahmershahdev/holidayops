"""Facts about every country at once, for the landing page: who is off today, how weekends
differ, and what's coming up. Building all ~250 calendars takes about 1.5 s cold, so each
snapshot is cached for the day."""

from dataclasses import dataclass
from datetime import date, timedelta

from django.core.cache import cache

from apps.core import get_calendar, list_countries
from apps.public.content import country_name, holiday_language, page_path

UPCOMING_DAYS = 21
UPCOMING_LIMIT = 10
# A few per day, so the rail spans a couple of weeks instead of one busy Monday.
UPCOMING_PER_DAY = 2
CACHE_SECONDS = 6 * 3600
# Countries most visitors recognise, shown first as examples of each weekend pattern.
FEATURED = ("US", "GB", "PK", "IN", "SA", "AE", "EG", "DE", "FR", "QA", "IR", "BN", "MX", "JP")


@dataclass(frozen=True)
class Place:
    code: str
    name: str
    path: str


@dataclass(frozen=True)
class Upcoming:
    day: date
    place: Place
    names: tuple[str, ...]


@dataclass(frozen=True)
class WeekendGroup:
    days: tuple[int, ...]
    count: int
    examples: tuple[Place, ...]


@dataclass(frozen=True)
class World:
    today: date
    holiday_today: tuple[Place, ...]
    weekend_today: int
    weekends: tuple[WeekendGroup, ...]
    upcoming: tuple[Upcoming, ...]


def _place(code: str, lang: str, year: int) -> Place:
    return Place(code, country_name(code, lang), page_path(lang, code, year))


def _rank(code: str) -> int:
    return FEATURED.index(code) if code in FEATURED else len(FEATURED)


def _featured(codes: list[str]) -> list[str]:
    return sorted(codes, key=_rank)


def build_world(today: date, lang: str) -> World:
    countries = list_countries()
    years = sorted({today.year, (today + timedelta(days=UPCOMING_DAYS)).year})
    holiday_today: list[Place] = []
    weekend_today = 0
    groups: dict[tuple[int, ...], list[str]] = {}
    upcoming: list[Upcoming] = []
    for code, info in countries.items():
        groups.setdefault(tuple(sorted(info.weekend)), []).append(code)
        # English when the library lacks the page language: a rail of mixed Spanish, French and
        # Thai names reads worse than one fallback language.
        language = holiday_language(info, lang) or holiday_language(info, "en")
        cal = get_calendar(code, None, years, language, ())
        if today in cal:
            holiday_today.append(_place(code, lang, today.year))
        elif today.weekday() in info.weekend:
            weekend_today += 1
        for offset in range(1, UPCOMING_DAYS + 1):
            day = today + timedelta(days=offset)
            if day in cal:
                upcoming.append(
                    Upcoming(day, _place(code, lang, day.year), tuple(cal.get_list(day)))
                )
                break
    upcoming.sort(key=lambda u: (u.day, _rank(u.place.code), u.place.name))
    per_day: dict[date, int] = {}
    spread = []
    for item in upcoming:
        per_day[item.day] = per_day.get(item.day, 0) + 1
        if per_day[item.day] <= UPCOMING_PER_DAY:
            spread.append(item)
    weekends = tuple(
        WeekendGroup(
            days, len(codes), tuple(_place(c, lang, today.year) for c in _featured(codes)[:4])
        )
        for days, codes in sorted(groups.items(), key=lambda g: -len(g[1]))
    )
    return World(
        today,
        tuple(sorted(holiday_today, key=lambda p: p.name)),
        weekend_today,
        weekends,
        tuple(spread[:UPCOMING_LIMIT]),
    )


def world(today: date, lang: str) -> World:
    key = f"world:{today.isoformat()}:{lang}"
    snapshot: World | None = cache.get(key)
    if snapshot is None:
        snapshot = build_world(today, lang)
        cache.set(key, snapshot, CACHE_SECONDS)
    return snapshot
