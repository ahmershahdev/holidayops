from datetime import date

import pytest

from apps.core import (
    CoreError,
    CustomDay,
    FeedEvent,
    YearNotCovered,
    build_ical,
    feed_events,
    get_calendar,
    merge_calendars,
)
from apps.core.ical import _fold


def merged(*custom: CustomDay, language: str = "en_US"):  # type: ignore[no-untyped-def]
    return merge_calendars([get_calendar("PK", None, [2027], language, ())], custom)


def test_feed_lists_holidays_in_range_in_date_order() -> None:
    events = feed_events(merged(), date(2027, 3, 1), date(2027, 12, 31))
    assert [e.day for e in events] == sorted(e.day for e in events)
    assert FeedEvent(date(2027, 3, 23), "Pakistan Day", "HOLIDAY") in events
    assert all(e.day >= date(2027, 3, 1) for e in events)
    assert date(2027, 2, 5) not in {e.day for e in events}


def test_custom_days_win_and_are_categorised() -> None:
    cal = merged(
        CustomDay(date(2027, 3, 23), "Office closed", "closure"),
        CustomDay(date(2027, 4, 5), "Early finish", "half_day"),
        CustomDay(date(2027, 4, 10), "Stock count", "working_day"),
        CustomDay(date(2027, 11, 30), "Outside range", "closure"),
    )
    events = {e.day: e for e in feed_events(cal, date(2027, 3, 1), date(2027, 4, 30))}
    assert events[date(2027, 3, 23)] == FeedEvent(date(2027, 3, 23), "Office closed", "CLOSURE")
    assert events[date(2027, 4, 5)].category == "HALF-DAY"
    assert events[date(2027, 4, 10)].category == "WORKING-DAY"
    assert date(2027, 11, 30) not in events


def test_feed_rejects_reversed_or_uncovered_range() -> None:
    with pytest.raises(CoreError):
        feed_events(merged(), date(2027, 5, 1), date(2027, 4, 1))
    with pytest.raises(YearNotCovered):
        feed_events(merged(), date(2027, 1, 1), date(2028, 1, 1))


def test_ical_document_shape() -> None:
    events = [FeedEvent(date(2027, 3, 23), "Pakistan Day", "HOLIDAY")]
    text = build_ical("Karachi office", "abc", events, date(2027, 1, 2))
    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert "\r\nUID:20270323@abc\r\n" in text
    assert "\r\nDTSTAMP:20270102T000000Z\r\n" in text
    assert "\r\nDTSTART;VALUE=DATE:20270323\r\nDTEND;VALUE=DATE:20270324\r\n" in text
    assert "\r\nCATEGORIES:HOLIDAY\r\n" in text
    assert "\n" not in text.replace("\r\n", "")


def test_ical_escapes_text() -> None:
    events = [FeedEvent(date(2027, 1, 1), "A, B; C\\D\nE\r\nF", "CLOSURE")]
    text = build_ical("Name, with; marks", "x", events, date(2027, 1, 1))
    assert "X-WR-CALNAME:Name\\, with\\; marks\r\n" in text
    assert "SUMMARY:A\\, B\\; C\\\\D\\nE\\nF\r\n" in text


def test_ical_dec_31_ends_next_year() -> None:
    text = build_ical("x", "x", [FeedEvent(date(2027, 12, 31), "x", "HOLIDAY")], date(2027, 1, 1))
    assert "DTEND;VALUE=DATE:20280101" in text


def test_short_lines_are_not_folded() -> None:
    assert _fold("SUMMARY:short") == "SUMMARY:short"


def test_long_lines_fold_at_75_octets_without_splitting_characters() -> None:
    line = "SUMMARY:" + "یومِ پاکستان " * 20
    folded = _fold(line)
    parts = folded.split("\r\n")
    assert len(parts) > 1
    assert all(len(p.encode()) <= 75 for p in parts)
    assert all(p.startswith(" ") for p in parts[1:])
    assert "".join([parts[0], *(p[1:] for p in parts[1:])]) == line


def test_urdu_holiday_names_survive_a_full_feed() -> None:
    events = feed_events(merged(language="ur_PK"), date(2027, 1, 1), date(2027, 12, 31))
    text = build_ical("کراچی", "x", events, date(2027, 1, 1))
    text.encode("utf-8")
    unfolded = text.replace("\r\n ", "")
    assert any(e.summary in unfolded for e in events if not e.summary.isascii())
