"""Context for the site frame (header, footer) shared by every server-rendered page."""

from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from django.http import HttpRequest
from django.utils import timezone

from apps.public.content import LANGUAGES, PREFIX, country_name, page_path
from apps.public.seo import OWNER, OWNER_URL, REPO_URL, SUPPORT_EMAIL
from apps.public.theme import get_theme

POPULAR = ("PK", "SA", "AE", "US", "GB", "IN")


def frame_context(
    request: HttpRequest, lang: str, path_for: Callable[[str], str] | None = None
) -> dict[str, Any]:
    year = timezone.now().year
    here = request.get_full_path()
    return {
        "lang": lang,
        "dir": "rtl" if lang in {"ur", "ar"} else "ltr",
        "prefix": PREFIX[lang],
        "home": f"{PREFIX[lang]}/",
        "theme": get_theme(request),
        "theme_next": quote(here, safe="/"),
        "languages": [
            (code, path_for(code) if path_for else f"{PREFIX[code]}/") for code in LANGUAGES
        ],
        "year": year,
        "popular": [(country_name(c, lang), page_path(lang, c, year)) for c in POPULAR],
        "repo_url": REPO_URL,
        "owner": OWNER,
        "owner_url": OWNER_URL,
        "support_email": SUPPORT_EMAIL,
    }
