from datetime import date

import pytest

from apps.core import (
    MAX_YEAR,
    MIN_YEAR,
    UnsupportedCategory,
    UnsupportedCountry,
    UnsupportedLanguage,
    UnsupportedSubdivision,
    YearOutOfRange,
    get_calendar,
    get_country,
    list_countries,
)


def test_list_countries_excludes_aliases_and_reads_metadata() -> None:
    countries = list_countries()
    assert "PK" in countries
    assert "PAK" not in countries
    sa = countries["SA"]
    assert sa.name == "Saudi Arabia"
    assert sa.weekend == (4, 5)
    assert sa.default_language == "ar"
    assert "public" in sa.categories


def test_country_name_splits_camel_case() -> None:
    assert get_country("AE").name == "United Arab Emirates"


def test_get_country_is_case_insensitive() -> None:
    assert get_country("pk").code == "PK"


def test_get_country_rejects_unknown_code() -> None:
    with pytest.raises(UnsupportedCountry) as exc:
        get_country("ZZ")
    assert exc.value.field == "country"


def test_get_calendar_builds_requested_years_only() -> None:
    cal = get_calendar("PK", None, [2027], None, ())
    assert cal.years == {2027}
    assert date(2027, 3, 23) in cal
    assert date(2028, 3, 23) not in cal
    assert cal.years == {2027}


def test_get_calendar_is_cached_for_equal_inputs() -> None:
    first = get_calendar("pk", None, [2028, 2027, 2027], None, ())
    second = get_calendar("PK", None, (2027, 2028), None, ("public",))
    assert first is second


def test_get_calendar_with_subdivision_language_and_categories() -> None:
    cal = get_calendar("US", "CA", [2027], "en_US", ("public", "government"))
    assert cal.subdiv == "CA"
    assert cal.categories == {"public", "government"}


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"subdiv": "ZZ"}, UnsupportedSubdivision),
        ({"language": "xx"}, UnsupportedLanguage),
        ({"categories": ("public", "nope")}, UnsupportedCategory),
        ({"years": []}, YearOutOfRange),
        ({"years": [MIN_YEAR - 1]}, YearOutOfRange),
        ({"years": [MAX_YEAR + 1]}, YearOutOfRange),
    ],
)
def test_get_calendar_validates_inputs(kwargs: dict[str, object], error: type[Exception]) -> None:
    args: dict[str, object] = {
        "country": "US",
        "subdiv": None,
        "years": [2027],
        "language": None,
        "categories": (),
    }
    args.update(kwargs)
    with pytest.raises(error):
        get_calendar(**args)  # type: ignore[arg-type]
