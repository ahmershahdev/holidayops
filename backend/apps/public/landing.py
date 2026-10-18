"""The landing page (`/`, `/ur/`, `/ar/`). Docs: docs/design/m6-showcase.md, 6.2."""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.api.serializers import CheckResultSerializer
from apps.core import CoreError, get_calendar, is_business_day, list_countries
from apps.public.content import (
    PREFIX,
    Cell,
    country_name,
    holiday_language,
    month_grid,
    page_path,
    week_headers,
    year_window,
)
from apps.public.seo import SUPPORT_EMAIL, fit_title, site_graph
from apps.public.views import PUBLIC_POLICY, _meta, public_page
from apps.public.world import world

# Country shown in the hero calendar and preselected in the demo, by page language, and the
# zone its "today" is read in: at 02:00 in Karachi it's still yesterday in UTC.
HOME_COUNTRY = {"en": "PK", "ur": "PK", "ar": "SA"}
HOME_ZONE = {"PK": ZoneInfo("Asia/Karachi"), "SA": ZoneInfo("Asia/Riyadh")}
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
    info = list_countries()[country]
    cal = get_calendar(country, None, [today.year], holiday_language(info, lang), ())
    return week_headers(info), month_grid(cal, info, today.replace(day=1), today)


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
        Answer(
            country_name(country, lang), day, result.is_business_day, result.reason, result.holidays
        ),
        "",
    )


def faq() -> list[tuple[str, str]]:
    return [
        (
            _("Where does the holiday data come from?"),
            _(
                "From holidays, an open-source Python library kept up to date by a large "
                "community. HolidayOps adds each country's weekend, moved working days and your "
                "own closures on top."
            ),
        ),
        (
            _("Does it know that weekends differ between countries?"),
            _(
                "Yes. Saudi Arabia rests on Friday and Saturday, Iran on Friday, Brunei on Friday "
                "and Sunday. Every answer uses the country's own weekend, including the years "
                "before a country changed it."
            ),
        ),
        (
            _("Can I add my company's own days off?"),
            _(
                "Yes. A company calendar merges any countries and regions with your closures, half "
                "days and extra working days, and the API, feeds and webhooks answer from it."
            ),
        ),
        (
            _("Is there a free plan?"),
            _(
                "Yes, free for good: 10,000 API requests a month, company calendars, iCal feeds, "
                "digests and webhooks. Pro raises the limits."
            ),
        ),
        (
            _("Which languages does it speak?"),
            _(
                "The site and the app are in English, Urdu and Arabic, laid out right to left "
                "where needed. Holiday names come in the country's own language when the library "
                "has it."
            ),
        ),
        (
            _("What if a date is wrong?"),
            _(
                "Write to %(email)s. Most fixes belong in the holidays library, and a fix there "
                "corrects the date for everyone who uses it."
            )
            % {"email": SUPPORT_EMAIL},
        ),
    ]


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
    countries = list_countries()
    home = HOME_COUNTRY[lang]
    today = timezone.localdate(timezone=HOME_ZONE[home])
    headers, weeks = month_cells(home, lang, today)
    values, answer, error = demo(request.GET.dict(), lang, today)
    curl, response_json = api_sample()
    now = world(today, lang)
    home_info = countries[home]
    home_cal = get_calendar(home, None, [today.year], holiday_language(home_info, lang), ())
    home_today = is_business_day(home_cal, today)
    questions = faq()
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/"),
        "title": _("Holidays and working days for every country"),
        "head_title": fit_title(_("Public holidays and working days API")),
        "description": _(
            "Is it a working day? Public holidays, local weekends and your own closures for 250 "
            "countries, through one API, iCal feeds and webhooks."
        ),
        "ld_site": site_graph(request, lang, questions),
        "faq": questions,
        "world": now,
        "working_today": len(countries) - len(now.holiday_today) - now.weekend_today,
        "week": [date(2027, 3, 22) + timedelta(days=n) for n in range(7)],
        "home_today": home_today,
        "home_reason": reason_label(home_today.reason),
        "home": f"{PREFIX[lang]}/",
        "country_count": len(countries),
        "region_count": sum(len(c.subdivisions) for c in countries.values()),
        "home_country": country_name(home, lang),
        "month": today,
        "weekday_headers": headers,
        "weeks": weeks,
        "choices": sorted(((c, country_name(c, lang)) for c in countries), key=lambda c: c[1]),
        "values": values,
        "answer": answer,
        "reason": reason_label(answer.reason) if answer else "",
        "error": error,
        "curl": curl,
        "response_json": response_json,
        "marquee": [(c, country_name(c, lang), page_path(lang, c, today.year)) for c in MARQUEE],
        "today": today,
    }
    response = render(request, "public/landing.html", context)
    response["Content-Security-Policy"] = LANDING_POLICY
    return response
