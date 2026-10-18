"""Titles, breadcrumbs and JSON-LD for the public pages. Docs: docs/seo.md."""

import json
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.templatetags.static import static
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext as _

from apps.public.content import PREFIX

SITE = "HolidayOps"
# Search results cut titles at about 60 characters and descriptions at about 150.
TITLE_MAX = 60
DESCRIPTION_MAX = 150
OWNER = "Syed Ahmer Shah"
OWNER_URL = "https://ahmershah.dev"
SUPPORT_EMAIL = "support@ahmershah.dev"
REPO_URL = "https://github.com/ahmershahdev/holidayops"
# Same escapes as Django's json_script, so a holiday name can never close the <script> element.
_JSON_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026"}


def fit_title(*candidates: str) -> str:
    """The first candidate that fits with the brand after it, else the first that fits alone."""
    for title in candidates:
        full = title if SITE in title else f"{title} · {SITE}"
        if len(full) <= TITLE_MAX:
            return full
    for title in candidates:
        if len(title) <= TITLE_MAX:
            return title
    return candidates[-1][: TITLE_MAX - 1] + "…"


def ld_json(data: Any) -> SafeString:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).translate(_JSON_ESCAPES)
    return mark_safe(f'<script type="application/ld+json">{text}</script>')  # noqa: S308


def breadcrumbs(request: HttpRequest, lang: str, items: list[tuple[str, str]]) -> dict[str, Any]:
    """Home first, the current page last; the same list feeds the visible trail and JSON-LD."""
    trail = [(_("Home"), f"{PREFIX[lang]}/"), *items]
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": n,
                "name": name,
                "item": request.build_absolute_uri(path),
            }
            for n, (name, path) in enumerate(trail, start=1)
        ],
    }
    return {"breadcrumbs": trail, "ld_breadcrumbs": ld_json(data)}


def site_graph(request: HttpRequest, lang: str, faq: list[tuple[str, str]]) -> SafeString:
    """Organization, WebSite, the web app with its free plan, and the landing FAQ."""
    root = request.build_absolute_uri("/")
    org = f"{root}#organization"
    free = settings.PLANS["free"]
    graph: list[dict[str, Any]] = [
        {
            "@type": "Organization",
            "@id": org,
            "name": SITE,
            "url": root,
            "logo": request.build_absolute_uri(static("public/icon-512.png")),
            "email": SUPPORT_EMAIL,
            "sameAs": [REPO_URL],
            "founder": {"@type": "Person", "name": OWNER, "url": OWNER_URL},
            "contactPoint": {
                "@type": "ContactPoint",
                "contactType": "customer support",
                "email": SUPPORT_EMAIL,
                "availableLanguage": ["en", "ur", "ar"],
            },
        },
        {
            "@type": "WebSite",
            "@id": f"{root}#website",
            "name": SITE,
            "url": root,
            "inLanguage": lang,
            "publisher": {"@id": org},
        },
        {
            "@type": "WebApplication",
            "name": SITE,
            "url": root,
            "applicationCategory": "BusinessApplication",
            "operatingSystem": "Any",
            "browserRequirements": "Requires a modern web browser",
            "publisher": {"@id": org},
            "offers": {
                "@type": "Offer",
                "name": _("Free"),
                "price": "0",
                "priceCurrency": "USD",
                "description": _("%(quota)s API requests a month")
                % {"quota": f"{int(free['monthly_quota']):,}"},
            },
        },
    ]
    if faq:
        graph.append(
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": question,
                        "acceptedAnswer": {"@type": "Answer", "text": answer},
                    }
                    for question, answer in faq
                ],
            }
        )
    return ld_json({"@context": "https://schema.org", "@graph": graph})
