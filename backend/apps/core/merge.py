import copy
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from holidays import HolidayBase

from apps.core.errors import CoreError

CustomKind = Literal["closure", "half_day", "working_day"]


@dataclass(frozen=True)
class CustomDay:
    day: date
    name: str
    kind: CustomKind


@dataclass(frozen=True)
class MergedCalendar:
    holidays: HolidayBase
    custom: Mapping[date, CustomDay] = field(default_factory=dict)
    sources: tuple[HolidayBase, ...] = ()

    @property
    def years(self) -> set[int]:
        return self.holidays.years


def merge_calendars(
    sources: Sequence[HolidayBase],
    custom: Iterable[CustomDay],
    weekend: Iterable[int] | None = None,
) -> MergedCalendar:
    if not sources:
        raise CoreError("A calendar needs at least one source.")
    merged = copy.copy(sources[0]) if len(sources) == 1 else sum(sources[1:], start=sources[0])
    # HolidaySum falls back to Sat-Sun and some countries (SA, AE) compute the weekend per date,
    # so the weekend rule is pinned on the instance: the first source's, or the company's own.
    if weekend is None:
        merged._get_weekend = sources[0]._get_weekend  # type: ignore[method-assign]
    else:
        fixed = set(weekend)
        merged._get_weekend = lambda dt: fixed  # type: ignore[method-assign]
    merged.weekend_workdays = set(merged.weekend_workdays)
    by_day = {item.day: item for item in custom}
    for item in by_day.values():
        if item.kind == "closure":
            merged[item.day] = item.name
            merged.weekend_workdays.discard(item.day)
        else:
            if item.day in merged:
                merged.pop(item.day)
            merged.weekend_workdays.add(item.day)
    return MergedCalendar(holidays=merged, custom=by_day, sources=tuple(sources))


def source_label(cal: HolidayBase) -> str:
    return f"{cal.country}-{cal.subdiv}" if cal.subdiv else str(cal.country)


def holiday_sources(cal: HolidayBase | MergedCalendar, day: date, name: str) -> tuple[str, ...]:
    if not isinstance(cal, MergedCalendar):
        return (source_label(cal),)
    return tuple(source_label(src) for src in cal.sources if name in src.get_list(day))
