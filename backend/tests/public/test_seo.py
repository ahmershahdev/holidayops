import html
import json
import re
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone, translation

from apps.core import list_countries
from apps.public.content import country_name
from apps.public.seo import DESCRIPTION_MAX, TITLE_MAX, fit_title
from apps.public.views import year_meta
from tests.factories import UserFactory

YEAR = timezone.now().year
PAGES = [
    "/",
    "/holidays/",
    f"/holidays/pk/{YEAR}/",
    "/holidays/pk/today/",
    "/today/",
    "/tools/overlap/",
    "/pricing/",
    "/about/",
    "/contact/",
]
ENGLISH_ONLY = ["/privacy/", "/terms/"]


def head(html_text: str) -> tuple[str, str]:
    title = re.search(r"<title>(.*?)</title>", html_text, re.S)
    description = re.search(r'<meta name="description" content="(.*?)">', html_text, re.S)
    assert title
    assert description
    return html.unescape(title.group(1)), html.unescape(description.group(1))


def ld_blocks(html_text: str) -> list[Any]:
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S)
    return [json.loads(block) for block in blocks]


def test_fit_title_adds_the_brand_only_when_it_fits() -> None:
    assert fit_title("Pricing") == "Pricing · HolidayOps"
    assert fit_title("About HolidayOps") == "About HolidayOps"
    long = "x" * 55
    assert fit_title(long, "short") == "short · HolidayOps"
    assert fit_title(long, "y" * 58) == long
    assert len(fit_title("z" * 80)) == TITLE_MAX


@pytest.mark.parametrize("prefix", ["", "/ur", "/ar"])
@pytest.mark.parametrize("path", PAGES)
def test_every_page_fits_search_result_limits(prefix: str, path: str) -> None:
    response = Client().get(f"{prefix}{path}")
    assert response.status_code == 200
    title, description = head(response.content.decode())
    assert len(title) <= TITLE_MAX, title
    assert 50 <= len(description) <= DESCRIPTION_MAX, description


@pytest.mark.parametrize("path", ENGLISH_ONLY)
def test_legal_pages_fit_and_are_english_only(path: str) -> None:
    response = Client().get(path)
    title, description = head(response.content.decode())
    assert len(title) <= TITLE_MAX
    assert len(description) <= DESCRIPTION_MAX
    page = response.content.decode()
    assert '<link rel="alternate" hreflang="ur"' not in page
    assert '<a href="/ur/" hreflang="ur"' in page
    assert Client().get(f"/ur{path}").status_code == 404


@pytest.mark.parametrize("lang", ["en", "ur", "ar"])
def test_year_titles_fit_for_every_country_and_region(lang: str) -> None:
    with translation.override(lang):
        for code, info in list_countries().items():
            name = country_name(code, lang)
            for place in [name, *(f"{name} ({s})" for s in info.subdivisions)]:
                _, title, description = year_meta(place, YEAR, 99, 366)
                assert len(title) <= TITLE_MAX, title
                assert len(description) <= DESCRIPTION_MAX, description


def test_breadcrumbs_are_visible_and_structured() -> None:
    page = Client().get(f"/holidays/pk/{YEAR}/").content.decode()
    assert '<nav class="crumbs"' in page
    assert '<span aria-current="page">Pakistan</span>' in page
    crumbs = next(b for b in ld_blocks(page) if b.get("@type") == "BreadcrumbList")
    items = crumbs["itemListElement"]
    assert [i["name"] for i in items] == ["Home", "Holidays", "Pakistan"]
    assert items[0]["item"] == "http://testserver/"
    assert "crumbs" not in Client().get("/").content.decode()


def test_landing_describes_the_site_owner_and_faq() -> None:
    page = Client().get("/").content.decode()
    (graph,) = (b["@graph"] for b in ld_blocks(page) if "@graph" in b)
    types = {node["@type"]: node for node in graph}
    org = types["Organization"]
    assert org["email"] == "support@ahmershah.dev"
    assert org["founder"]["url"] == "https://ahmershah.dev"
    assert [o["price"] for o in types["WebApplication"]["offers"]] == ["0", "19"]
    questions = types["FAQPage"]["mainEntity"]
    assert len(questions) == page.count("<summary>")
    assert all(q["acceptedAnswer"]["text"] for q in questions)


def test_every_page_has_social_cards_and_a_manifest() -> None:
    page = Client().get("/pricing/").content.decode()
    assert 'property="og:image" content="http://testserver/static/public/og-image.png"' in page
    assert '<meta name="twitter:card" content="summary_large_image">' in page
    assert '<link rel="manifest" href="/manifest.webmanifest">' in page
    assert "apple-touch-icon.png" in page


def test_footer_credits_the_owner() -> None:
    page = Client().get("/about/").content.decode()
    assert '<a href="https://ahmershah.dev" rel="author">Syed Ahmer Shah</a>' in page
    assert 'href="mailto:support@ahmershah.dev"' in page
    for path in ("/about/", "/contact/", "/privacy/", "/terms/"):
        assert f'href="{path}"' in page


@pytest.mark.django_db
def test_signed_in_visitors_get_their_own_header() -> None:
    out = Client().get("/about/").content.decode()
    assert 'href="/signup"' in out
    client = Client()
    client.force_login(UserFactory.create())
    page = client.get("/about/").content.decode()
    assert 'href="/signup"' not in page
    assert 'href="/app">' in page
    assert 'href="/signup"' in Client().get("/about/").content.decode()


def test_no_inline_styles_on_public_pages() -> None:
    for path in ("/", "/about/", "/nope-404/"):
        response = Client().get(path)
        assert "unsafe-inline" not in response["Content-Security-Policy"]
        assert "manifest-src 'self'" in response["Content-Security-Policy"]
        assert "camera=()" in response["Permissions-Policy"]
