from dataclasses import dataclass
from datetime import date
from typing import Literal

from holidays import HolidayBase

from apps.core.errors import YearNotCovered
from apps.core.merge import CustomKind, MergedCalendar

Calendar = HolidayBase | MergedCalendar
Reason = Literal[
    "working_day",
    "weekend",
    "holiday",
    "weekend_workday",
    "closure",
    "half_day",
    "custom_working_day",
]

CUSTOM_REASONS: dict[CustomKind, Reason] = {
    "closure": "closure",
    "half_day": "half_day",
    "working_day": "custom_working_day",
}


@dataclass(frozen=True)
class BusinessDayResult:
    day: date
    is_business_day: bool
    reason: Reason
    holidays: tuple[str, ...]
    half_day: bool = False


def _holidays(cal: Calendar) -> HolidayBase:
    return cal.holidays if isinstance(cal, MergedCalendar) else cal


def _require_years(cal: Calendar, first: date, last: date) -> None:
    missing = set(range(first.year, last.year + 1)) - cal.years
    if missing:
        raise YearNotCovered(f"Calendar does not cover year {min(missing)}.")


def _is_weekend(cal: HolidayBase, day: date) -> bool:
    # Weekends can change by date (the UAE moved from Fri-Sat to Sat-Sun in 2022), so ask the
    # library per date instead of reading the class-level `weekend`.
    return day.weekday() in cal._get_weekend(day)


def is_business_day(cal: Calendar, day: date) -> BusinessDayResult:
    _require_years(cal, day, day)
    base = _holidays(cal)
    names = tuple(base.get_list(day))
    working = base.is_working_day(day)
    custom = cal.custom.get(day) if isinstance(cal, MergedCalendar) else None
    reason: Reason
    if custom is not None:
        reason = CUSTOM_REASONS[custom.kind]
        if custom.kind == "half_day":
            names = (custom.name,)
    elif _is_weekend(base, day):
        reason = "weekend_workday" if working else "weekend"
    else:
        reason = "holiday" if names else "working_day"
    half_day = custom is not None and custom.kind == "half_day"
    return BusinessDayResult(day, working, reason, names, half_day)


def add_business_days(cal: Calendar, start: date, n: int) -> date:
    _require_years(cal, start, start)
    result = _holidays(cal).get_nth_working_day(start, n)
    _require_years(cal, min(start, result), max(start, result))
    return result


def business_days_between(cal: Calendar, start: date, end: date) -> int:
    _require_years(cal, min(start, end), max(start, end))
    return _holidays(cal).get_working_days_count(start, end)
