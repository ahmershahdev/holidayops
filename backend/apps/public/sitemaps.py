from typing import Any

from django.contrib.sitemaps import Sitemap
from django.utils import timezone, translation

from apps.core import list_countries
from apps.public.content import LANGUAGES, PREFIX, SITEMAP_YEARS, page_path


# Sitemap is generic only in django-stubs, not at runtime.
class _Localized(Sitemap):  # type: ignore[type-arg]
    i18n = True
    languages = list(LANGUAGES)
    alternates = True
    x_default = True


class PagesSitemap(_Localized):
    changefreq = "monthly"

    def items(self) -> list[str]:
        return [
            "/",
            "/today/",
            "/tools/overlap/",
            "/holidays/",
            "/pricing/",
            "/about/",
            "/contact/",
        ]

    def location(self, item: str) -> str:
        return f"{PREFIX[translation.get_language()]}{item}"


class LegalSitemap(Sitemap):  # type: ignore[type-arg]
    """English only: see apps/public/pages.py."""

    changefreq = "yearly"

    def items(self) -> list[str]:
        return ["/privacy/", "/terms/"]

    def location(self, item: str) -> str:
        return item


class CountrySitemap(_Localized):
    changefreq = "monthly"

    def __init__(self, code: str) -> None:
        self.code = code

    def items(self) -> list[tuple[int, str | None] | str]:
        this_year = timezone.now().year
        places: list[str | None] = [None, *list_countries()[self.code].subdivisions]
        years = [(this_year + offset, place) for offset in SITEMAP_YEARS for place in places]
        return ["today", *years]

    def location(self, item: tuple[int, str | None] | str) -> str:
        lang = translation.get_language()
        if isinstance(item, str):
            return f"{PREFIX[lang]}/holidays/{self.code.lower()}/today/"
        year, subdiv = item
        return page_path(lang, self.code, year, subdiv)


def sitemaps() -> "dict[str, Sitemap[Any]]":
    sections: dict[str, Sitemap[Any]] = {"pages": PagesSitemap(), "legal": LegalSitemap()}
    for code in sorted(list_countries()):
        sections[code.lower()] = CountrySitemap(code)
    return sections
