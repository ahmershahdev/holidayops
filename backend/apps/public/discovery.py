"""Files for crawlers, language models and installers: robots.txt, llms.txt, llms-full.txt, the
web app manifest and the service worker. Docs: docs/seo.md."""

import json
from datetime import date, timedelta

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.cache import cache_page

from apps.api.serializers import CheckResultSerializer
from apps.core import get_calendar, is_business_day, list_countries
from apps.public.content import weekend_names
from apps.public.seo import OWNER, OWNER_URL, REPO_URL, SITE, SUPPORT_EMAIL
from apps.public.views import build_id

DAY = 24 * 3600
TEXT = "text/plain; charset=utf-8"


def robots(request: HttpRequest) -> HttpResponse:
    lines = [
        "User-agent: *",
        "Disallow: /app/",
        "Disallow: /api/",
        "Disallow: /feeds/",
        "Disallow: /invite",
        "Disallow: /unsubscribe",
        "Disallow: /forgot-password",
        "Disallow: /theme/",
        "Disallow: /offline/",
        # The docs and schema are meant to be read; the rest of /api/ is data.
        "Allow: /api/v1/docs/",
        "Allow: /api/v1/schema/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type=TEXT)


def _about(request: HttpRequest) -> dict[str, object]:
    countries = list_countries()
    return {
        "root": request.build_absolute_uri("/"),
        "country_count": len(countries),
        "region_count": sum(len(c.subdivisions) for c in countries.values()),
        "owner": OWNER,
        "owner_url": OWNER_URL,
        "support_email": SUPPORT_EMAIL,
        "repo_url": REPO_URL,
    }


@cache_page(DAY)
def llms(request: HttpRequest) -> HttpResponse:
    return render(request, "public/llms.txt", _about(request), content_type=TEXT)


@cache_page(DAY)
def llms_full(request: HttpRequest) -> HttpResponse:
    year = timezone.now().year
    # A Friday: a weekend day in Saudi Arabia, which is the point of the example.
    friday = date(year, 4, 1) + timedelta(days=(4 - date(year, 4, 1).weekday()) % 7)
    cal = get_calendar("SA", None, [year], "en_US", ())
    check = CheckResultSerializer(is_business_day(cal, friday)).data
    context = {
        **_about(request),
        "year": year,
        "check_date": friday.isoformat(),
        "check_example": json.dumps(check),
        "plans": [{"name": code.title(), **limits} for code, limits in settings.PLANS.items()],
        "countries": [
            {
                "code": info.code,
                "name": info.name,
                "weekend": weekend_names(info, "en"),
                "regions": len(info.subdivisions),
            }
            for info in sorted(list_countries().values(), key=lambda c: c.code)
        ],
    }
    return render(request, "public/llms-full.txt", context, content_type=TEXT)


def manifest(request: HttpRequest) -> JsonResponse:
    icons = [
        {"src": static("public/icon-192.png"), "sizes": "192x192", "type": "image/png"},
        {"src": static("public/icon-512.png"), "sizes": "512x512", "type": "image/png"},
        {
            "src": static("public/icon-maskable-512.png"),
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable",
        },
        {"src": static("public/icon.svg"), "sizes": "any", "type": "image/svg+xml"},
    ]
    data = {
        "id": "/",
        "name": SITE,
        "short_name": SITE,
        "description": "Public holidays and working days for every country, merged with your "
        "own company calendar.",
        "start_url": "/playground",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0a1428",
        "theme_color": "#0b1b3f",
        "lang": "en",
        "dir": "auto",
        "categories": ["business", "productivity", "utilities"],
        "icons": icons,
        "shortcuts": [
            {"name": "Is it a working day?", "url": "/playground"},
            {"name": "Public holidays", "url": "/holidays/"},
            {"name": "My calendars", "url": "/app"},
        ],
    }
    response = JsonResponse(data, json_dumps_params={"ensure_ascii": False})
    response["Content-Type"] = "application/manifest+json"
    return response


def service_worker(request: HttpRequest) -> HttpResponse:
    offline = "/offline/"
    precache = [offline, static("public/site.css"), static("public/icon-192.png")]
    context = {
        "version": json.dumps(build_id()),
        "offline": json.dumps(offline),
        "precache": json.dumps(precache),
    }
    response = render(request, "public/sw.js", context, content_type="text/javascript")
    # Browsers check for a new worker on navigation; a cached copy would pin the old one.
    response["Cache-Control"] = "no-cache"
    response["Content-Security-Policy"] = "default-src 'self'"
    return response
