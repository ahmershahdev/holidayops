import json
import re
from datetime import date
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from apps.core import business_days_between, get_calendar
from apps.public.content import YEARS_AROUND
from apps.public.seo import ld_json
from apps.public.views import PUBLIC_POLICY

YEAR = timezone.now().year


@pytest.fixture
def web() -> Client:
    return Client()


def ld_blocks(html: str) -> list[Any]:
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return [json.loads(block) for block in blocks]


def test_country_index(web: Client) -> None:
    response = web.get("/holidays/")
    assert response.status_code == 200
    html = response.content.decode()
    assert f'href="/holidays/pk/{YEAR}/"' in html
    assert '<link rel="canonical" href="http://testserver/holidays/">' in html
    for code, path in (("en", ""), ("ur", "/ur"), ("ar", "/ar")):
        assert f'hreflang="{code}" href="http://testserver{path}/holidays/"' in html
    assert 'hreflang="x-default" href="http://testserver/holidays/"' in html
    assert response["Content-Security-Policy"] == PUBLIC_POLICY
    assert response["Content-Language"] == "en"
    assert response["Cache-Control"] == "no-cache"


def test_year_page_lists_every_holiday_with_structured_data(web: Client) -> None:
    response = web.get(f"/holidays/pk/{YEAR}/")
    assert response.status_code == 200
    html = response.content.decode()
    cal = get_calendar("PK", None, [YEAR], "en_US", ())
    assert f"<title>Public holidays in Pakistan {YEAR} · HolidayOps</title>" in html
    assert f'<time datetime="{YEAR}-03-23">' in html
    assert "Pakistan Day" in html
    working = business_days_between(cal, date(YEAR, 1, 1), date(YEAR, 12, 31))
    assert f"<strong>{working}</strong>" in html
    assert "<strong>Saturday and Sunday</strong>" in html

    breadcrumbs, events = ld_blocks(html)
    assert breadcrumbs["@type"] == "BreadcrumbList"
    assert [i["name"] for i in breadcrumbs["itemListElement"]] == ["Home", "Holidays", "Pakistan"]
    names = {e["name"] for e in events}
    assert names == {name for day in cal for name in cal.get_list(day)}
    assert all(e["@type"] == "Event" and e["location"]["name"] == "Pakistan" for e in events)
    assert f"/api/v1/holidays/?country=PK&amp;year={YEAR}" in html


def test_urdu_page_is_rtl_with_urdu_holiday_names(web: Client) -> None:
    response = web.get(f"/ur/holidays/pk/{YEAR}/")
    assert response.status_code == 200
    html = response.content.decode()
    assert '<html lang="ur" dir="rtl" data-theme="system">' in html
    assert f'<link rel="canonical" href="http://testserver/ur/holidays/pk/{YEAR}/">' in html
    urdu = get_calendar("PK", None, [YEAR], "ur_PK", ())
    assert urdu.get(date(YEAR, 3, 23)) in html
    assert response["Content-Language"] == "ur"
    assert "Public holidays in" not in html


def test_arabic_page_uses_arabic_names_where_the_country_has_them(web: Client) -> None:
    html = web.get(f"/ar/holidays/sa/{YEAR}/").content.decode()
    assert '<html lang="ar" dir="rtl" data-theme="system">' in html
    arabic = get_calendar("SA", None, [YEAR], "ar", ())
    assert next(iter(arabic.values())) in html


def test_subdivision_pages(web: Client) -> None:
    response = web.get(f"/holidays/us/ca/{YEAR}/")
    assert response.status_code == 200
    html = response.content.decode()
    assert f"Public holidays in United States (CA) {YEAR}" in html
    assert f'href="/holidays/us/{YEAR}/"' in html
    assert "César Chávez Day" in html or "Cesar Chavez Day" in html
    assert web.get(f"/holidays/us/zz/{YEAR}/").status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        f"/holidays/xx/{YEAR}/",
        f"/holidays/pk/{YEAR + YEARS_AROUND + 1}/",
        f"/holidays/pk/{YEAR - YEARS_AROUND - 1}/",
        f"/fr/holidays/pk/{YEAR}/",
        "/holidays/xx/",
    ],
)
def test_unknown_pages_are_404(web: Client, path: str) -> None:
    assert web.get(path).status_code == 404


def test_country_without_year_redirects_to_this_year(web: Client) -> None:
    assert web.get("/holidays/PK/")["Location"] == f"/holidays/pk/{YEAR}/"
    assert web.get("/ar/holidays/pk/")["Location"] == f"/ar/holidays/pk/{YEAR}/"


def test_year_navigation_stops_at_the_window(web: Client) -> None:
    middle = web.get(f"/holidays/pk/{YEAR}/").content.decode()
    assert f'href="/holidays/pk/{YEAR - 1}/" rel="prev"' in middle
    assert f'href="/holidays/pk/{YEAR + 1}/" rel="next"' in middle
    edge = web.get(f"/holidays/pk/{YEAR + YEARS_AROUND}/").content.decode()
    assert 'rel="next"' not in edge


def test_json_ld_cannot_break_out_of_its_script() -> None:
    block = ld_json({"name": "</script><script>alert(1)</script> & co"})
    assert "</script><script>" not in block
    payload = block.removeprefix('<script type="application/ld+json">').removesuffix("</script>")
    assert json.loads(payload)["name"] == "</script><script>alert(1)</script> & co"


def test_pricing_page_follows_the_plan_settings(web: Client, settings: Any) -> None:
    settings.PLANS = {**settings.PLANS, "pro": {**settings.PLANS["pro"], "max_keys": 42}}
    html = web.get("/pricing/").content.decode()
    assert '<dd class="ltr">42</dd>' in html
    assert '<dd class="ltr">120</dd>' in html
    assert '<dd class="ltr">10K</dd>' in html
    assert '<td class="ltr">10,000</td>' in html
    assert '<td class="ltr">1,000,000</td>' in html


def test_robots_txt(web: Client) -> None:
    text = web.get("/robots.txt").content.decode()
    assert "Disallow: /app/" in text
    assert "Disallow: /api/" in text
    assert "Sitemap: http://testserver/sitemap.xml" in text


def test_sitemap_index_and_country_sections(web: Client) -> None:
    index = web.get("/sitemap.xml").content.decode()
    assert "http://testserver/sitemap-pk.xml" in index
    assert "http://testserver/sitemap-pages.xml" in index

    pk = web.get("/sitemap-pk.xml").content.decode()
    assert f"<loc>http://testserver/holidays/pk/{YEAR}/</loc>" in pk
    assert f"<loc>http://testserver/ur/holidays/pk/{YEAR + 2}/</loc>" in pk
    assert f'hreflang="ar" href="http://testserver/ar/holidays/pk/{YEAR}/"' in pk
    assert f"/holidays/pk/{YEAR + 3}/" not in pk

    us = web.get("/sitemap-us.xml").content.decode()
    assert f"<loc>http://testserver/holidays/us/ca/{YEAR}/</loc>" in us
    assert web.get("/sitemap-nope.xml").status_code == 404


def test_api_keeps_reading_accept_language(web: Client) -> None:
    response = web.get("/api/v1/holidays/?country=XX&year=2027", HTTP_ACCEPT_LANGUAGE="ur")
    assert response.status_code == 400
    assert "XX" in response.content.decode()
    assert response.headers["Content-Language"] == "ur"


def test_style_guide_is_noindex_with_its_own_policy(web: Client) -> None:
    response = web.get("/style/")
    assert response.status_code == 200
    html = response.content.decode()
    assert '<meta name="robots" content="noindex">' in html
    assert "#0b1b3f" in html
    assert "'unsafe-inline'" in response["Content-Security-Policy"]
    assert "'unsafe-inline'" not in web.get("/pricing/")["Content-Security-Policy"]
    assert "/style/" not in web.get("/sitemap-pages.xml").content.decode()


def test_public_pages_load_the_display_font(web: Client) -> None:
    html = web.get("/holidays/").content.decode()
    assert 'rel="preload"' in html
    assert "outfit-latin-wght-normal" in html
    assert "font-src 'self'" in web.get("/holidays/")["Content-Security-Policy"]
