import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache, lru_cache

import holidays
from holidays import HolidayBase
from holidays.constants import PUBLIC

from apps.core.errors import (
    UnsupportedCategory,
    UnsupportedCountry,
    UnsupportedLanguage,
    UnsupportedSubdivision,
    YearOutOfRange,
)

MIN_YEAR = 1970
MAX_YEAR = 2100


@dataclass(frozen=True)
class CountryInfo:
    code: str
    name: str
    subdivisions: tuple[str, ...]
    languages: tuple[str, ...]
    default_language: str | None
    categories: tuple[str, ...]
    weekend: tuple[int, ...]


def _country_name(cal: HolidayBase, code: str) -> str:
    # country_holidays("PK") returns an alias class named "PK"; the readable name is on its parent.
    base = next(cls for cls in type(cal).__mro__ if cls.__name__ != code)
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base.__name__)


@cache
def list_countries() -> dict[str, CountryInfo]:
    countries = {}
    for code in holidays.list_supported_countries(include_aliases=False):
        cal = holidays.country_holidays(code, years=())
        countries[code] = CountryInfo(
            code=code,
            name=_country_name(cal, code),
            subdivisions=tuple(cal.subdivisions),
            languages=tuple(cal.supported_languages),
            default_language=cal.default_language,
            categories=tuple(cal.supported_categories),
            weekend=tuple(sorted(cal.weekend)),
        )
    return countries


def get_country(code: str) -> CountryInfo:
    try:
        return list_countries()[code.upper()]
    except KeyError:
        raise UnsupportedCountry(f"Country {code!r} is not supported.") from None


def get_calendar(
    country: str,
    subdiv: str | None,
    years: Iterable[int],
    language: str | None,
    categories: tuple[str, ...],
) -> HolidayBase:
    info = get_country(country)
    if subdiv is not None and subdiv not in info.subdivisions:
        raise UnsupportedSubdivision(f"Subdivision {subdiv!r} is not supported for {info.code}.")
    if language is not None and language not in info.languages:
        raise UnsupportedLanguage(f"Language {language!r} is not supported for {info.code}.")
    unknown = sorted(set(categories) - set(info.categories))
    if unknown:
        raise UnsupportedCategory(
            f"Categories not supported for {info.code}: {', '.join(unknown)}."
        )
    year_tuple = tuple(sorted(set(years)))
    if not year_tuple or year_tuple[0] < MIN_YEAR or year_tuple[-1] > MAX_YEAR:
        raise YearOutOfRange(f"Years must be between {MIN_YEAR} and {MAX_YEAR}.")
    category_tuple = tuple(sorted(set(categories))) or (PUBLIC,)
    # language=None makes the library guess from the server locale, so names would vary by host.
    language = language or info.default_language
    return _build_calendar(info.code, subdiv, year_tuple, language, category_tuple)


@lru_cache(maxsize=256)
def _build_calendar(
    country: str,
    subdiv: str | None,
    years: tuple[int, ...],
    language: str | None,
    categories: tuple[str, ...],
) -> HolidayBase:
    return holidays.country_holidays(
        country,
        subdiv=subdiv,
        years=years,
        expand=False,
        language=language,
        categories=categories,
    )
