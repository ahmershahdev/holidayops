"""The landing page (`/`, `/ur/`, `/ar/`). Docs: docs/design/m6-showcase.md, 6.2."""

import json
from dataclasses import dataclass
from datetime import date, timedelta

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.api.serializers import CheckResultSerializer
from apps.core import CoreError, get_calendar, is_business_day, list_countries
from apps.public.content import PREFIX, holiday_language, page_path, year_window
from apps.public.views import PUBLIC_POLICY, _meta, public_page

# Country shown in the hero calendar and preselected in the demo, by page language.
HOME_COUNTRY = {"en": "PK", "ur": "PK", "ar": "SA"}
MARQUEE = (
    "PK",
    "SA",
    "AE",
    "US",
    "GB",
    "IN",
    "DE",
    "FR",
    "TR",
    "EG",
    "BD",
    "ID",
    "MY",
    "QA",
    "KW",
    "OM",
    "BH",
    "JP",
    "BR",
    "CA",
    "AU",
    "NG",
    "KE",
    "ZA",
    "ES",
    "IT",
    "NL",
    "SE",
    "MX",
    "CN",
)
# The demo form posts back here; everything else on the page stays as strict as other pages.
LANDING_POLICY = PUBLIC_POLICY.replace("form-action 'none'", "form-action 'self'").replace(
    "style-src 'self'", "style-src 'self' 'unsafe-inline'"
)


@dataclass(frozen=True)
class Cell:
    day: date | None
    kind: str
    names: tuple[str, ...] = ()


@dataclass(frozen=True)
class Answer:
    country: str
    day: date
    working: bool
    reason: str
    names: tuple[str, ...]


def reason_label(reason: str) -> str:
    return {
        "working_day": _("a working day"),
        "weekend": _("a weekend day"),
        "holiday": _("a public holiday"),
        "weekend_workday": _("a working weekend day (moved working day)"),
    }.get(reason, reason)


def month_cells(country: str, lang: str, today: date) -> tuple[list[date], list[list[Cell]]]:
    """The current month as weeks of cells, starting the day after the country's weekend."""
    info = list_countries()[country]
    cal = get_calendar(country, None, [today.year], holiday_language(info, lang), ())
    week_start = (max(info.weekend) + 1) % 7 if info.weekend else 0
    first = today.replace(day=1)
    lead = (first.weekday() - week_start) % 7
    headers = [date(2027, 3, 22) + timedelta(days=(week_start + n) % 7) for n in range(7)]
    cells: list[Cell] = [Cell(None, "pad")] * lead
    day = first
    while day.month == first.month:
        names = tuple(cal.get_list(day))
        if names:
            kind = "holiday"
        elif day.weekday() in info.weekend:
            kind = "weekend"
        else:
            kind = "work"
        if day == today:
            kind += " today"
        cells.append(Cell(day, kind, names))
        day += timedelta(days=1)
    cells += [Cell(None, "pad")] * (-len(cells) % 7)
    return headers, [cells[i : i + 7] for i in range(0, len(cells), 7)]


def demo(
    params: dict[str, str], lang: str, today: date
) -> tuple[dict[str, str], Answer | None, str]:
    """The no-JS 'is it a working day?' form: validated input in, an answer or an error out."""
    country = params.get("country", HOME_COUNTRY[lang]).upper()[:3]
    raw_day = params.get("date", today.isoformat())[:10]
    values = {"country": country, "date": raw_day}
    if "country" not in params and "date" not in params:
        return values, None, ""
    info = list_countries().get(country)
    try:
        day = date.fromisoformat(raw_day)
    except ValueError:
        return values, None, _("Pick a valid date.")
    if info is None:
        return values, None, _("Pick a country from the list.")
    if day.year not in year_window(today):
        return values, None, _("Pick a date within five years of today.")
    try:
        cal = get_calendar(country, None, [day.year], holiday_language(info, lang), ())
        result = is_business_day(cal, day)
    except CoreError:
        return values, None, _("That date can't be checked.")
    return (
        values,
        Answer(info.name, day, result.is_business_day, result.reason, result.holidays),
        "",
    )


def api_sample() -> tuple[str, str]:
    day = date(timezone.now().year, 3, 23)
    cal = get_calendar("PK", None, [day.year], "en_US", ())
    body = json.dumps(CheckResultSerializer(is_business_day(cal, day)).data, indent=2)
    return (
        f'curl "https://holidayops.ahmershah.dev/api/v1/business-days/check/?country=PK&date={day}"',
        body,
    )


@public_page
def landing(request: HttpRequest, lang: str) -> HttpResponse:
    today = timezone.now().date()
    countries = list_countries()
    home = HOME_COUNTRY[lang]
    headers, weeks = month_cells(home, lang, today)
    values, answer, error = demo(request.GET.dict(), lang, today)
    curl, response_json = api_sample()
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/"),
        "title": _("Holidays and working days for every country"),
        "description": _(
            "HolidayOps answers “is it a working day?” for 250 countries and their regions, "
            "merged with your own company closures, through a fast API, iCal feeds and webhooks."
        ),
        "home": f"{PREFIX[lang]}/",
        "country_count": len(countries),
        "region_count": sum(len(c.subdivisions) for c in countries.values()),
        "home_country": countries[home],
        "month": today,
        "weekday_headers": headers,
        "weeks": weeks,
        "choices": sorted(((c.code, c.name) for c in countries.values()), key=lambda c: c[1]),
        "values": values,
        "answer": answer,
        "reason": reason_label(answer.reason) if answer else "",
        "error": error,
        "curl": curl,
        "response_json": response_json,
        "marquee": [(countries[c].name, page_path(lang, c, today.year)) for c in MARQUEE],
        "today": today,
    }
    response = render(request, "public/landing.html", context)
    response["Content-Security-Policy"] = LANDING_POLICY
    return response
