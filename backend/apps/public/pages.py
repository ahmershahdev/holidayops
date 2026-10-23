"""About, contact, legal and offline pages. Legal pages are English only: a translation of a
policy nobody has reviewed would promise things the English one doesn't."""

from datetime import date

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core import list_countries
from apps.public.content import PREFIX
from apps.public.seo import SUPPORT_EMAIL, breadcrumbs, fit_title
from apps.public.status import checks, releases
from apps.public.views import _meta, public_page

LEGAL_UPDATED = date(2026, 10, 18)


@public_page
def about(request: HttpRequest, lang: str) -> HttpResponse:
    countries = list_countries()
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/about/"),
        **breadcrumbs(request, lang, [(_("About"), f"{PREFIX[lang]}/about/")]),
        "title": _("About HolidayOps"),
        "head_title": fit_title(_("About HolidayOps and who builds it")),
        "description": _(
            "Why HolidayOps exists, where its holiday data comes from, and the person who "
            "builds it."
        ),
        "country_count": len(countries),
        "region_count": sum(len(c.subdivisions) for c in countries.values()),
    }
    return render(request, "public/about.html", context)


@public_page
def guide(request: HttpRequest, lang: str) -> HttpResponse:
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/guide/"),
        **breadcrumbs(request, lang, [(_("Guide"), f"{PREFIX[lang]}/guide/")]),
        "title": _("How to use HolidayOps"),
        "head_title": fit_title(_("How to use HolidayOps: a step-by-step guide")),
        "description": _(
            "From your first date check to a shared company calendar, iCal feeds and the API, "
            "one step at a time."
        ),
        "origin": request.build_absolute_uri("/").rstrip("/"),
        "docs": reverse("docs"),
        "support": SUPPORT_EMAIL,
    }
    return render(request, "public/guide.html", context)


@public_page
def contact(request: HttpRequest, lang: str) -> HttpResponse:
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/contact/"),
        **breadcrumbs(request, lang, [(_("Contact"), f"{PREFIX[lang]}/contact/")]),
        "title": _("Contact and support"),
        "description": _(
            "Questions, Pro plans, wrong dates or a security report: how to reach the people "
            "behind HolidayOps."
        ),
    }
    return render(request, "public/contact.html", context)


def _legal(request: HttpRequest, lang: str, path: str, name: str) -> dict[str, object]:
    return {
        # The language switch leads to that language's home page: there is no translation.
        **_meta(request, lang, lambda code: path if code == "en" else f"{PREFIX[code]}/", ("en",)),
        **breadcrumbs(request, lang, [(name, path)]),
        "updated": LEGAL_UPDATED,
    }


@public_page
def privacy(request: HttpRequest, lang: str) -> HttpResponse:
    context = {
        **_legal(request, lang, "/privacy/", "Privacy"),
        "title": "Privacy policy",
        "description": "What HolidayOps stores, why, for how long, and how to get it deleted. "
        "No ads, no trackers, no selling data.",
        "free_quota": settings.PLANS["free"]["monthly_quota"],
    }
    return render(request, "public/privacy.html", context)


@public_page
def terms(request: HttpRequest, lang: str) -> HttpResponse:
    context = {
        **_legal(request, lang, "/terms/", "Terms"),
        "title": "Terms of service",
        "description": "The rules for using HolidayOps: accounts, API keys, fair use, and why "
        "you should check dates that matter.",
    }
    return render(request, "public/terms.html", context)


@public_page
def offline(request: HttpRequest, lang: str) -> HttpResponse:
    """Shown by the service worker when a page can't be reached; precached at install."""
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/offline/"),
        "title": _("You're offline"),
        "description": _("This page needs a connection. Check your network and try again."),
        "noindex": True,
        "canonical": None,
    }
    return render(request, "public/offline.html", context)


@public_page
def status(request: HttpRequest, lang: str) -> HttpResponse:
    results = checks()
    context = {
        **_meta(request, lang, lambda code: f"{PREFIX[code]}/status/"),
        **breadcrumbs(request, lang, [(_("Status"), f"{PREFIX[lang]}/status/")]),
        "title": _("System status"),
        "head_title": fit_title(_("System status")),
        "description": _(
            "Live health of the HolidayOps API, website, database, background jobs and holiday "
            "data, checked on every visit."
        ),
        "checks": results,
        "all_ok": all(c.ok for c in results),
        "checked_at": timezone.now(),
    }
    response = render(request, "public/status.html", context)
    response.live = True  # type: ignore[attr-defined]
    return response


@public_page
def changelog(request: HttpRequest, lang: str) -> HttpResponse:
    context = {
        **_legal(request, lang, "/changelog/", "Changelog"),
        "title": "Changelog",
        "description": "Every notable change to HolidayOps, newest first: features, fixes and "
        "security improvements.",
        "releases": releases(),
    }
    return render(request, "public/changelog.html", context)
