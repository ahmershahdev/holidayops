from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from apps.core.business_days import _require_years
from apps.core.errors import CoreError
from apps.core.merge import CustomKind, MergedCalendar

Category = Literal["HOLIDAY", "CLOSURE", "HALF-DAY", "WORKING-DAY"]

CUSTOM_CATEGORIES: dict[CustomKind, Category] = {
    "closure": "CLOSURE",
    "half_day": "HALF-DAY",
    "working_day": "WORKING-DAY",
}


@dataclass(frozen=True)
class FeedEvent:
    day: date
    summary: str
    category: Category


def feed_events(cal: MergedCalendar, start: date, end: date) -> list[FeedEvent]:
    if end < start:
        raise CoreError("End must not be before start.")
    _require_years(cal, start, end)
    events = {
        day: FeedEvent(day, "; ".join(cal.holidays.get_list(day)), "HOLIDAY")
        for day in cal.holidays
        if start <= day <= end
    }
    for custom in cal.custom.values():
        if start <= custom.day <= end:
            events[custom.day] = FeedEvent(custom.day, custom.name, CUSTOM_CATEGORIES[custom.kind])
    return [events[day] for day in sorted(events)]


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    # RFC 5545 3.1: lines are at most 75 octets; continuation lines start with one space. Count
    # UTF-8 bytes and never split a character, or Urdu and Arabic names come out corrupted.
    parts: list[str] = []
    chunk, size = "", 0
    for char in line:
        width = len(char.encode())
        if size + width > (74 if parts else 75):
            parts.append(chunk)
            chunk, size = "", 0
        chunk += char
        size += width
    parts.append(chunk)
    return "\r\n ".join(parts)


def build_ical(name: str, uid_domain: str, events: Iterable[FeedEvent], stamp: date) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//HolidayOps//Feeds//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)}",
    ]
    for event in events:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{event.day:%Y%m%d}@{uid_domain}",
            f"DTSTAMP:{stamp:%Y%m%d}T000000Z",
            f"DTSTART;VALUE=DATE:{event.day:%Y%m%d}",
            f"DTEND;VALUE=DATE:{event.day + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_escape(event.summary)}",
            f"CATEGORIES:{event.category}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "".join(f"{_fold(line)}\r\n" for line in lines)
