from dataclasses import dataclass
from datetime import date
from typing import Literal

from holidays import HolidayBase

from apps.core.errors import YearNotCovered

Reason = Literal["working_day", "weekend", "holiday", "weekend_workday"]


@dataclass(frozen=True)
class BusinessDayResult:
    day: date
    is_business_day: bool
    reason: Reason
    holidays: tuple[str, ...]


def _require_years(cal: HolidayBase, first: date, last: date) -> None:
    missing = set(range(first.year, last.year + 1)) - cal.years
    if missing:
        raise YearNotCovered(f"Calendar does not cover year {min(missing)}.")


def _is_weekend(cal: HolidayBase, day: date) -> bool:
    # Weekends can change by date (the UAE moved from Fri-Sat to Sat-Sun in 2022), so ask the
    # library per date instead of reading the class-level `weekend`.
    return day.weekday() in cal._get_weekend(day)


def is_business_day(cal: HolidayBase, day: date) -> BusinessDayResult:
    _require_years(cal, day, day)
    names = tuple(cal.get_list(day))
    working = cal.is_working_day(day)
    reason: Reason
    if _is_weekend(cal, day):
        reason = "weekend_workday" if working else "weekend"
    else:
        reason = "holiday" if names else "working_day"
    return BusinessDayResult(day=day, is_business_day=working, reason=reason, holidays=names)


def add_business_days(cal: HolidayBase, start: date, n: int) -> date:
    _require_years(cal, start, start)
    result = cal.get_nth_working_day(start, n)
    _require_years(cal, min(start, result), max(start, result))
    return result


def business_days_between(cal: HolidayBase, start: date, end: date) -> int:
    _require_years(cal, min(start, end), max(start, end))
    return cal.get_working_days_count(start, end)
