import json
from collections.abc import Callable
from datetime import date, timedelta
from functools import wraps
from typing import Any

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_page

from apps.core import list_countries
from apps.public.content import (
    LANGUAGES,
    PREFIX,
    YearPage,
    find_country,
    find_subdivision,
    page_path,
    year_page,
    year_window,
)

CACHE_SECONDS = 6 * 3600
# No JavaScript at all: the pages are plain HTML and one stylesheet. JSON-LD blocks are data, not
# script, so script-src 'none' doesn't affect them.
PUBLIC_POLICY = (
    "default-src 'none'; style-src 'self'; img-src 'self' data:; script-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
# Same escapes as Django's json_script, so a holiday name can never close the <script> element.
_JSON_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026"}

View = Callable[..., HttpResponse]


def public_page(view: View) -> View:
    @wraps(view)
    def wrapper(request: HttpRequest, *args: Any, lang: str = "en", **kwargs: Any) -> HttpResponse:
        with translation.override(lang):
            response = view(request, *args, lang=lang, **kwargs)
        response["Content-Language"] = lang
        response["Content-Security-Policy"] = PUBLIC_POLICY
        response["Cache-Control"] = f"public, max-age={CACHE_SECONDS // 6}"
        return response

    return cache_page(CACHE_SECONDS)(wrapper)


def ld_json(data: Any) -> SafeString:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).translate(_JSON_ESCAPES)
    return mark_safe(f'<script type="application/ld+json">{text}</script>')  # noqa: S308


def _meta(request: HttpRequest, lang: str, path_for: Callable[[str], str]) -> dict[str, Any]:
    alternates = [(code, request.build_absolute_uri(path_for(code))) for code in LANGUAGES]
    return {
        "lang": lang,
        "dir": "rtl" if lang in {"ur", "ar"} else "ltr",
        "canonical": request.build_absolute_uri(path_for(lang)),
        "alternates": alternates,
        "x_default": alternates[0][1],
        "prefix": PREFIX[lang],
        "languages": [(code, path_for(code)) for code in LANGUAGES],
    }


def _breadcrumbs(request: HttpRequest, items: list[tuple[str, str]]) -> SafeString:
    return ld_json(
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": n,
                    "name": name,
                    "item": request.build_absolute_uri(path),
                }
                for n, (name, path) in enumerate(items, start=1)
            ],
        }
    )


@public_page
def country_index(request: HttpRequest, lang: str) -> HttpResponse:
    year = timezone.now().year
    countries = sorted(list_countries().values(), key=lambda c: c.name)
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/holidays/"),
        "title": _("Public holidays by country"),
        "description": _(
            "Public holidays and working days for %(count)s countries, with the dates for "
            "every year."
        )
        % {"count": len(countries)},
        "countries": [(c, page_path(lang, c.code, year)) for c in countries],
        "year": year,
    }
    return render(request, "public/index.html", context)


def country_latest(request: HttpRequest, country: str, lang: str = "en") -> HttpResponse:
    info = find_country(country)
    if info is None:
        raise Http404
    return redirect(page_path(lang, info.code, timezone.now().year))


@public_page
def year_view(
    request: HttpRequest, country: str, year: int, lang: str, subdiv: str | None = None
) -> HttpResponse:
    info = find_country(country)
    code = find_subdivision(info, subdiv) if info and subdiv else None
    if info is None or (subdiv and code is None) or year not in year_window(timezone.now().date()):
        raise Http404
    page = year_page(info, code, year, lang)
    place = f"{info.name} ({code})" if code else info.name
    title = _("Public holidays in %(place)s %(year)s") % {"place": place, "year": year}
    description = _(
        "All %(count)s public holidays in %(place)s in %(year)s, with dates, weekdays and "
        "%(working)s working days."
    ) % {"count": len(page.holidays), "place": place, "year": year, "working": page.working_days}
    crumbs = [
        (_("Holidays"), f"{PREFIX[lang]}/holidays/"),
        (info.name, page_path(lang, info.code, year)),
    ]
    if code:
        crumbs.append((code, page_path(lang, info.code, year, code)))
    window = year_window(timezone.now().date())
    context = {
        **_meta(request, lang, lambda c: page_path(c, info.code, year, code)),
        "title": title,
        "description": description,
        "page": page,
        "place": place,
        "weekend": [date(2027, 3, 22) + timedelta(days=d) for d in info.weekend],
        "previous": page_path(lang, info.code, year - 1, code) if year - 1 in window else None,
        "next": page_path(lang, info.code, year + 1, code) if year + 1 in window else None,
        "country_path": page_path(lang, info.code, year) if code else None,
        "subdivisions": [(s, page_path(lang, info.code, year, s)) for s in info.subdivisions],
        "breadcrumbs": crumbs,
        "ld_breadcrumbs": _breadcrumbs(request, crumbs),
        "ld_events": _events(page, place),
        "api_example": request.build_absolute_uri(
            f"/api/v1/holidays/?country={info.code}{f'&subdiv={code}' if code else ''}&year={year}"
        ),
    }
    return render(request, "public/year.html", context)


def _events(page: YearPage, place: str) -> SafeString:
    return ld_json(
        [
            {
                "@context": "https://schema.org",
                "@type": "Event",
                "name": name,
                "startDate": row.day.isoformat(),
                "endDate": row.day.isoformat(),
                "eventStatus": "https://schema.org/EventScheduled",
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "location": {"@type": "Country", "name": place},
            }
            for row in page.holidays
            for name in row.names
        ]
    )


@public_page
def pricing(request: HttpRequest, lang: str) -> HttpResponse:
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/pricing/"),
        "title": _("Pricing"),
        "description": _("API plans for HolidayOps: requests per minute, per month and API keys."),
        "plans": [{"code": code, **limits} for code, limits in settings.PLANS.items()],
        "signup": "/signup",
        "docs": reverse("docs"),
    }
    return render(request, "public/pricing.html", context)


def robots(request: HttpRequest) -> HttpResponse:
    lines = [
        "User-agent: *",
        "Disallow: /app/",
        "Disallow: /api/",
        "Disallow: /feeds/",
        "Disallow: /invite",
        "Disallow: /unsubscribe",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")
