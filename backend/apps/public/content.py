from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache

from babel import Locale
from babel.dates import format_date
from babel.lists import format_list
from holidays import HolidayBase

from apps.core import (
    CountryInfo,
    business_days_between,
    get_calendar,
    list_countries,
)

LANGUAGES = ("en", "ur", "ar")
PREFIX = {"en": "", "ur": "/ur", "ar": "/ar"}
YEARS_AROUND = 5
SITEMAP_YEARS = (-1, 0, 1, 2)
# The library's language codes to try for each UI language, best first.
HOLIDAY_LANGUAGES = {
    "en": ("en_US", "en_GB", "en"),
    "ur": ("ur_PK", "ur"),
    "ar": ("ar", "ar_QA", "ar_SA", "ar_AE", "ar_EG"),
}


@dataclass(frozen=True)
class HolidayRow:
    day: date
    names: tuple[str, ...]


@dataclass(frozen=True)
class Cell:
    day: date | None
    kind: str
    names: tuple[str, ...] = ()


@dataclass(frozen=True)
class YearPage:
    country: CountryInfo
    subdiv: str | None
    year: int
    holidays: tuple[HolidayRow, ...]
    working_days: int
    months: tuple[tuple[date, list[list[Cell]]], ...]


def year_window(today: date) -> range:
    return range(today.year - YEARS_AROUND, today.year + YEARS_AROUND + 1)


def holiday_language(country: CountryInfo, ui_language: str) -> str | None:
    for code in HOLIDAY_LANGUAGES[ui_language]:
        if code in country.languages:
            return code
    english = next((c for c in country.languages if c.startswith("en")), None)
    return english if ui_language == "en" else None


def find_country(code: str) -> CountryInfo | None:
    return list_countries().get(code.upper())


def find_subdivision(country: CountryInfo, code: str) -> str | None:
    return next((s for s in country.subdivisions if s.lower() == code.lower()), None)


def year_page(
    country: CountryInfo, subdiv: str | None, year: int, ui_language: str, today: date
) -> YearPage:
    cal = get_calendar(country.code, subdiv, [year], holiday_language(country, ui_language), ())
    rows = tuple(HolidayRow(day, tuple(cal.get_list(day))) for day in sorted(cal))
    working = business_days_between(cal, date(year, 1, 1), date(year, 12, 31))
    months = tuple(
        (date(year, m, 1), month_grid(cal, country, date(year, m, 1), today)) for m in range(1, 13)
    )
    return YearPage(country, subdiv, year, rows, working, months)


@cache
def _territories(language: str) -> dict[str, str]:
    return dict(Locale.parse(language).territories)


def country_name(code: str, language: str) -> str:
    """The library's names on English pages; CLDR's elsewhere, the same data the web app gets
    from Intl.DisplayNames, so both halves of the site agree."""
    english = list_countries()[code].name
    return english if language == "en" else _territories(language).get(code, english)


def join_list(items: Iterable[str], language: str) -> str:
    """CLDR list pattern: "Friday and Saturday", «الجمعة والسبت», «جمعہ اور ہفتہ»."""
    return format_list(list(items), locale=language)


def weekend_names(country: CountryInfo, language: str) -> str:
    days = (date(2027, 3, 22) + timedelta(days=d) for d in country.weekend)
    return join_list((format_date(d, "EEEE", locale=language) for d in days), language)


def week_start(country: CountryInfo) -> int:
    return (max(country.weekend) + 1) % 7 if country.weekend else 0


def week_headers(country: CountryInfo) -> list[date]:
    start = week_start(country)
    return [date(2027, 3, 22) + timedelta(days=(start + n) % 7) for n in range(7)]


def month_grid(
    cal: HolidayBase, country: CountryInfo, first: date, today: date
) -> list[list[Cell]]:
    """One month as weeks of cells, each week starting the day after the country's weekend."""
    cells: list[Cell] = [Cell(None, "pad")] * ((first.weekday() - week_start(country)) % 7)
    day = first
    while day.month == first.month:
        names = tuple(cal.get_list(day))
        if names:
            kind = "holiday"
        elif day.weekday() in country.weekend:
            kind = "weekend"
        else:
            kind = "work"
        if day == today:
            kind += " today"
        cells.append(Cell(day, kind, names))
        day += timedelta(days=1)
    cells += [Cell(None, "pad")] * (-len(cells) % 7)
    return [cells[i : i + 7] for i in range(0, len(cells), 7)]


def page_path(language: str, country: str, year: int, subdiv: str | None = None) -> str:
    middle = f"{country.lower()}/{subdiv.lower()}" if subdiv else country.lower()
    return f"{PREFIX[language]}/holidays/{middle}/{year}/"
