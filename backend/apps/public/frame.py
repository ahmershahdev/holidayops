"""Context for the site frame (header, footer) shared by every server-rendered page."""

from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from django.http import HttpRequest
from django.utils import timezone

from apps.core import list_countries
from apps.public.content import LANGUAGES, PREFIX, page_path
from apps.public.theme import get_theme

POPULAR = ("PK", "SA", "AE", "US", "GB", "IN")
REPO_URL = "https://github.com/ahmershahdev/holidayops"


def frame_context(
    request: HttpRequest, lang: str, path_for: Callable[[str], str] | None = None
) -> dict[str, Any]:
    year = timezone.now().year
    here = request.get_full_path()
    countries = list_countries()
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
        "popular": [(countries[c].name, page_path(lang, c, year)) for c in POPULAR],
        "repo_url": REPO_URL,
    }
