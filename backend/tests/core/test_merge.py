from datetime import date

import pytest

from apps.core import (
    CoreError,
    CustomDay,
    add_business_days,
    business_days_between,
    get_calendar,
    holiday_sources,
    is_business_day,
    merge_calendars,
)


def cal(country: str):  # type: ignore[no-untyped-def]
    return get_calendar(country, None, [2027], "en_US", ())


def test_merge_requires_a_source() -> None:
    with pytest.raises(CoreError):
        merge_calendars([], [])


def test_merge_unions_holidays_and_keeps_first_source_weekend() -> None:
    merged = merge_calendars([cal("PK"), cal("SA")], [])
    assert is_business_day(merged, date(2027, 3, 23)).reason == "holiday"
    assert is_business_day(merged, date(2027, 2, 22)).reason == "holiday"
    assert is_business_day(merged, date(2027, 4, 3)).reason == "weekend"
    assert is_business_day(merged, date(2027, 4, 2)).reason == "working_day"


def test_single_source_keeps_its_per_date_weekend() -> None:
    merged = merge_calendars([get_calendar("AE", None, [2021, 2022], "en_US", ())], [])
    assert is_business_day(merged, date(2021, 12, 31)).reason == "weekend"
    assert is_business_day(merged, date(2022, 1, 7)).is_business_day is True


def test_company_weekend_overrides_source_weekend() -> None:
    merged = merge_calendars([cal("SA")], [], weekend=[5, 6])
    assert is_business_day(merged, date(2027, 4, 2)).is_business_day is True
    assert is_business_day(merged, date(2027, 4, 3)).reason == "weekend"


def test_custom_days_win_over_sources() -> None:
    custom = [
        CustomDay(date(2027, 4, 5), "Office move", "closure"),
        CustomDay(date(2027, 3, 23), "Payroll run", "half_day"),
        CustomDay(date(2027, 4, 3), "Stocktake", "working_day"),
        CustomDay(date(2027, 3, 24), "Quarter close", "working_day"),
    ]
    merged = merge_calendars([cal("PK")], custom)

    closure = is_business_day(merged, date(2027, 4, 5))
    assert (closure.is_business_day, closure.reason, closure.holidays) == (
        False,
        "closure",
        ("Office move",),
    )

    half = is_business_day(merged, date(2027, 3, 23))
    assert (half.is_business_day, half.reason, half.half_day, half.holidays) == (
        True,
        "half_day",
        True,
        ("Payroll run",),
    )

    extra = is_business_day(merged, date(2027, 4, 3))
    assert (extra.is_business_day, extra.reason) == (True, "custom_working_day")
    assert is_business_day(merged, date(2027, 3, 24)).reason == "custom_working_day"


def test_closure_on_a_moved_working_day_closes_it() -> None:
    ru = get_calendar("RU", None, [2025], "en_US", ())
    merged = merge_calendars([ru], [CustomDay(date(2025, 11, 1), "Retreat", "closure")])
    assert is_business_day(merged, date(2025, 11, 1)).is_business_day is False


def test_merge_does_not_mutate_cached_sources() -> None:
    pk = cal("PK")
    merge_calendars([pk], [CustomDay(date(2027, 3, 23), "Open", "working_day")])
    assert is_business_day(pk, date(2027, 3, 23)).reason == "holiday"
    assert pk.weekend_workdays == set()


def test_maths_on_merged_calendar() -> None:
    merged = merge_calendars(
        [cal("PK")],
        [
            CustomDay(date(2027, 3, 25), "Closed", "closure"),
            CustomDay(date(2027, 3, 27), "Open Saturday", "working_day"),
        ],
    )
    assert add_business_days(merged, date(2027, 3, 24), 2) == date(2027, 3, 27)
    assert business_days_between(merged, date(2027, 3, 22), date(2027, 3, 28)) == 4


def test_holiday_sources_attributes_each_name() -> None:
    pk, sa = cal("PK"), cal("SA")
    us_ca = get_calendar("US", "CA", [2027], "en_US", ())
    merged = merge_calendars([pk, sa, us_ca], [])
    assert holiday_sources(merged, date(2027, 3, 23), "Pakistan Day") == ("PK",)
    assert holiday_sources(merged, date(2027, 2, 22), "Founding Day Holiday") == ("SA",)
    assert holiday_sources(merged, date(2027, 1, 1), "New Year's Day") == ("US-CA",)
    assert holiday_sources(pk, date(2027, 3, 23), "Pakistan Day") == ("PK",)
