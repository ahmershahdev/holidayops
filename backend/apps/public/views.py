import hashlib
from collections.abc import Callable
from functools import cache as memoize
from functools import wraps
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.cache import patch_vary_headers
from django.utils.safestring import SafeString
from django.utils.translation import gettext as _
from rest_framework.throttling import SimpleRateThrottle

from apps.core import list_countries
from apps.public.content import (
    LANGUAGES,
    PREFIX,
    YearPage,
    country_name,
    find_country,
    find_subdivision,
    page_path,
    week_headers,
    weekend_names,
    year_page,
    year_window,
)
from apps.public.frame import frame_context, signed_in
from apps.public.palette import swatches
from apps.public.patterns import pattern
from apps.public.seo import breadcrumbs, fit_title, ld_json
from apps.public.theme import get_theme
from config.security_log import security_event

CACHE_SECONDS = 6 * 3600
# No JavaScript at all: the pages are plain HTML and one stylesheet. JSON-LD blocks are data, not
# script, so script-src 'none' doesn't affect them. connect-src 'self' lets audit tools (e.g.
# Lighthouse) fetch /robots.txt from the page.
PUBLIC_POLICY = (
    "default-src 'none'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
    "script-src 'none'; connect-src 'self'; manifest-src 'self'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'"
)

View = Callable[..., HttpResponse]


class PublicPageThrottle(SimpleRateThrottle):
    scope = "public"

    # Used on plain Django views: the throttle only reads request.META, which both have.
    def allow_request(self, request: Any, view: Any) -> bool:
        return super().allow_request(request, view)

    def get_cache_key(self, request: Any, view: Any) -> str:
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


def too_many_requests(request: HttpRequest, wait: float | None) -> HttpResponse:
    security_event("rate_limited", request, scope="public")
    response = HttpResponse(
        _("Too many requests. Wait a minute and try again."),
        status=429,
        content_type="text/plain; charset=utf-8",
    )
    response["Retry-After"] = str(int(wait or 60))
    return response


@memoize
def build_id() -> str:
    """Changes with every deploy's static files. Cached pages name hashed stylesheets, so a page
    cached before a deploy would point at files that no longer exist."""
    try:
        return hashlib.sha256((settings.STATIC_ROOT / "staticfiles.json").read_bytes()).hexdigest()[
            :12
        ]
    except OSError:
        return "dev"


def public_page(view: View) -> View:
    """Language from the URL, strict CSP, and a server-side page cache keyed by theme: the
    theme is written into the HTML, so one cached copy per theme. Browsers revalidate the HTML
    (no-cache) so a theme switch shows at once; static files keep long cache lifetimes."""

    @wraps(view)
    def wrapper(request: HttpRequest, *args: Any, lang: str = "en", **kwargs: Any) -> HttpResponse:
        # The hour keeps "today" on the landing and the year calendars current: a page cached
        # before midnight would otherwise ring yesterday until the cache expired.
        hour = timezone.now().strftime("%Y%m%d%H")
        # Signed-in visitors see "My calendars" instead of log in / start free: one cached copy
        # each way, never anything about the person.
        who = "in" if signed_in(request) else "out"
        key = (
            f"page:{build_id()}:{hour}:{who}:{get_theme(request)}:{request.get_host()}:"
            f"{request.get_full_path()}"
        )
        cached: HttpResponse | None = cache.get(key)
        if cached is not None:
            return cached
        throttle = PublicPageThrottle()
        if not throttle.allow_request(request, None):
            with translation.override(lang):
                return too_many_requests(request, throttle.wait())
        with translation.override(lang):
            response = view(request, *args, lang=lang, **kwargs)
        response["Content-Language"] = lang
        response.setdefault("Content-Security-Policy", PUBLIC_POLICY)
        response["Cache-Control"] = "no-cache"
        patch_vary_headers(response, ["Cookie"])
        # Query strings (the landing demo) aren't cached: arbitrary keys would flood the cache.
        # Live pages (status) opt out with `response.live = True`.
        if response.status_code == 200 and not request.GET and not getattr(response, "live", False):
            cache.set(key, response, CACHE_SECONDS)
        return response

    return wrapper


def _meta(
    request: HttpRequest,
    lang: str,
    path_for: Callable[[str], str],
    languages: tuple[str, ...] = LANGUAGES,
) -> dict[str, Any]:
    alternates = [(code, request.build_absolute_uri(path_for(code))) for code in languages]
    return {
        "lang": lang,
        "dir": "rtl" if lang in {"ur", "ar"} else "ltr",
        "canonical": request.build_absolute_uri(path_for(lang)),
        "alternates": alternates,
        "x_default": alternates[0][1],
        **frame_context(request, lang, path_for),
    }


@public_page
def country_index(request: HttpRequest, lang: str) -> HttpResponse:
    year = timezone.now().year
    countries = sorted(list_countries(), key=lambda c: country_name(c, lang))
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/holidays/"),
        **breadcrumbs(request, lang, [(_("Holidays"), f"{PREFIX[lang]}/holidays/")]),
        "title": _("Public holidays by country"),
        "description": _(
            "Public holidays and working days for %(count)s countries, with the dates for "
            "every year."
        )
        % {"count": len(countries)},
        "countries": [(c, country_name(c, lang), page_path(lang, c, year)) for c in countries],
        "year": year,
    }
    return render(request, "public/index.html", context)


def country_latest(request: HttpRequest, country: str, lang: str = "en") -> HttpResponse:
    info = find_country(country)
    if info is None:
        raise Http404
    return redirect(page_path(lang, info.code, timezone.now().year))


def year_meta(place: str, year: int, count: int, working: int) -> tuple[str, str, str]:
    """The heading, the <title> and the meta description of a year page."""
    title = _("Public holidays in %(place)s %(year)s") % {"place": place, "year": year}
    head_title = fit_title(
        title,
        _("%(place)s holidays %(year)s") % {"place": place, "year": year},
        f"{place} {year}",
    )
    description = _(
        "All %(count)s public holidays in %(place)s in %(year)s, with dates, weekdays and "
        "%(working)s working days."
    ) % {"count": count, "place": place, "year": year, "working": working}
    return title, head_title, description


@public_page
def year_view(
    request: HttpRequest, country: str, year: int, lang: str, subdiv: str | None = None
) -> HttpResponse:
    info = find_country(country)
    code = find_subdivision(info, subdiv) if info and subdiv else None
    if info is None or (subdiv and code is None) or year not in year_window(timezone.now().date()):
        raise Http404
    page = year_page(info, code, year, lang, timezone.now().date())
    name = country_name(info.code, lang)
    place = f"{name} ({code})" if code else name
    title, head_title, description = year_meta(place, year, len(page.holidays), page.working_days)
    crumbs = [
        (_("Holidays"), f"{PREFIX[lang]}/holidays/"),
        (name, page_path(lang, info.code, year)),
    ]
    if code:
        crumbs.append((code, page_path(lang, info.code, year, code)))
    window = year_window(timezone.now().date())
    context = {
        **_meta(request, lang, lambda c: page_path(c, info.code, year, code)),
        "title": title,
        "head_title": head_title,
        "description": description,
        "page": page,
        "place": place,
        "country_code": info.code,
        "country_name": name,
        "pattern": pattern(info.code),
        "weekend": weekend_names(info, lang),
        "weekday_headers": week_headers(info),
        "previous": page_path(lang, info.code, year - 1, code) if year - 1 in window else None,
        "next": page_path(lang, info.code, year + 1, code) if year + 1 in window else None,
        "country_path": page_path(lang, info.code, year) if code else None,
        "subdivisions": [(s, page_path(lang, info.code, year, s)) for s in info.subdivisions],
        **breadcrumbs(request, lang, crumbs),
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


def plan_card(code: str, limits: dict[str, str | int]) -> dict[str, object]:
    """A plan's limits as the pricing page shows them: "120/minute" -> 120, 10000 -> "10K"."""
    quota = int(limits["monthly_quota"])
    short = f"{quota // 1_000_000}M" if quota >= 1_000_000 else f"{quota // 1000}K"
    return {
        "code": code,
        **limits,
        "per_minute": int(str(limits["rate"]).split("/")[0]),
        "monthly_short": short if quota >= 1000 else str(quota),
    }


@public_page
def pricing(request: HttpRequest, lang: str) -> HttpResponse:
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/pricing/"),
        **breadcrumbs(request, lang, [(_("Pricing"), f"{PREFIX[lang]}/pricing/")]),
        "title": _("Pricing"),
        "head_title": fit_title(_("Pricing: free and Pro API plans")),
        "description": _(
            "Start free with 10,000 API requests a month. Every plan includes company calendars, "
            "iCal feeds, digests and webhooks."
        ),
        "plans": [plan_card(code, limits) for code, limits in settings.PLANS.items()],
        "included": [
            _("Company calendars"),
            _("iCal feeds"),
            _("Monthly digests"),
            _("Signed webhooks"),
            _("Usage chart"),
        ],
        "signup": "/signup",
        "docs": reverse("docs"),
    }
    return render(request, "public/pricing.html", context)


@public_page
def style_guide(request: HttpRequest, lang: str) -> HttpResponse:
    """Living style guide for the showcase (docs/design/m6-showcase.md); not indexed."""
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/style/"),
        "title": "Style guide",
        "description": "HolidayOps palette, type and motion primitives.",
        "swatches": swatches(),
        "noindex": True,
    }
    response = render(request, "public/style.html", context)
    # Internal page with no user content: swatches and the motion path use inline styles.
    response["Content-Security-Policy"] = PUBLIC_POLICY.replace(
        "style-src 'self'", "style-src 'self' 'unsafe-inline'"
    )
    return response
