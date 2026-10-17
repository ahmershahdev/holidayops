from dataclasses import dataclass
from datetime import date

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
class YearPage:
    country: CountryInfo
    subdiv: str | None
    year: int
    holidays: tuple[HolidayRow, ...]
    working_days: int


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


def year_page(country: CountryInfo, subdiv: str | None, year: int, ui_language: str) -> YearPage:
    cal = get_calendar(country.code, subdiv, [year], holiday_language(country, ui_language), ())
    rows = tuple(HolidayRow(day, tuple(cal.get_list(day))) for day in sorted(cal))
    working = business_days_between(cal, date(year, 1, 1), date(year, 12, 31))
    return YearPage(country, subdiv, year, rows, working)


def page_path(language: str, country: str, year: int, subdiv: str | None = None) -> str:
    middle = f"{country.lower()}/{subdiv.lower()}" if subdiv else country.lower()
    return f"{PREFIX[language]}/holidays/{middle}/{year}/"
