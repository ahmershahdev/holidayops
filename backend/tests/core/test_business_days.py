from datetime import date

import pytest

from apps.core import (
    YearNotCovered,
    add_business_days,
    business_days_between,
    get_calendar,
    is_business_day,
)


def pk(*years: int):  # type: ignore[no-untyped-def]
    return get_calendar("PK", None, years or [2027], None, ())


@pytest.mark.parametrize(
    ("country", "day", "working", "reason", "names"),
    [
        ("PK", date(2027, 3, 24), True, "working_day", ()),
        ("PK", date(2027, 3, 23), False, "holiday", ("Pakistan Day",)),
        ("PK", date(2027, 3, 20), False, "weekend", ()),
        ("SA", date(2027, 4, 2), False, "weekend", ()),
        ("SA", date(2027, 4, 4), True, "working_day", ()),
        ("RU", date(2025, 11, 1), True, "weekend_workday", ()),
        ("PK", date(2026, 5, 28), False, "holiday", ("Eid al-Adha (estimated)", "Youm-e-Takbeer")),
    ],
)
def test_is_business_day(
    country: str, day: date, working: bool, reason: str, names: tuple[str, ...]
) -> None:
    cal = get_calendar(country, None, [day.year], None, ())
    result = is_business_day(cal, day)
    assert result.day == day
    assert result.is_business_day is working
    assert result.reason == reason
    assert result.holidays == names


def test_weekend_holiday_is_reported_as_weekend_with_names() -> None:
    result = is_business_day(pk(), date(2027, 12, 25))
    assert result.reason == "weekend"
    assert result.holidays == ("Quaid-e-Azam Day",)


def test_weekend_follows_the_date_not_the_current_rule() -> None:
    cal = get_calendar("AE", None, [2021, 2022], None, ())
    assert is_business_day(cal, date(2021, 12, 31)).reason == "weekend"
    assert is_business_day(cal, date(2022, 1, 7)).is_business_day is True
    assert is_business_day(cal, date(2022, 1, 8)).reason == "weekend"


def test_is_business_day_rejects_uncovered_year() -> None:
    with pytest.raises(YearNotCovered):
        is_business_day(pk(), date(2028, 1, 3))


@pytest.mark.parametrize(
    ("start", "n", "expected"),
    [
        (date(2027, 3, 20), 5, date(2027, 3, 29)),
        (date(2027, 3, 29), -5, date(2027, 3, 19)),
        (date(2027, 3, 24), 0, date(2027, 3, 24)),
        (date(2027, 3, 20), 0, date(2027, 3, 22)),
    ],
)
def test_add_business_days(start: date, n: int, expected: date) -> None:
    assert add_business_days(pk(), start, n) == expected


def test_add_business_days_across_years() -> None:
    assert add_business_days(pk(2027, 2028), date(2027, 12, 31), 1) == date(2028, 1, 3)


def test_add_business_days_rejects_uncovered_start() -> None:
    with pytest.raises(YearNotCovered):
        add_business_days(pk(), date(2026, 12, 31), 1)


def test_add_business_days_rejects_result_outside_calendar() -> None:
    with pytest.raises(YearNotCovered):
        add_business_days(pk(), date(2027, 12, 31), 1)


def test_between_is_inclusive_of_both_ends() -> None:
    cal = pk()
    assert business_days_between(cal, date(2027, 3, 24), date(2027, 3, 24)) == 1
    assert business_days_between(cal, date(2027, 3, 20), date(2027, 3, 20)) == 0
    assert business_days_between(cal, date(2027, 3, 22), date(2027, 3, 26)) == 4
    assert business_days_between(cal, date(2027, 3, 1), date(2027, 3, 31)) == 19


def test_between_accepts_reversed_range() -> None:
    assert business_days_between(pk(), date(2027, 3, 26), date(2027, 3, 22)) == 4


def test_between_rejects_uncovered_years() -> None:
    with pytest.raises(YearNotCovered):
        business_days_between(pk(), date(2027, 12, 1), date(2028, 1, 31))
