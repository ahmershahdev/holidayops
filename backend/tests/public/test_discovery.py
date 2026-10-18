import json

from django.contrib.staticfiles import finders
from django.test import Client


def test_robots_points_to_the_sitemap_and_keeps_data_out() -> None:
    text = Client().get("/robots.txt").content.decode()
    assert "Disallow: /api/" in text
    assert "Allow: /api/v1/docs/" in text
    assert "Sitemap: http://testserver/sitemap.xml" in text


def test_llms_txt_follows_the_format() -> None:
    response = Client().get("/llms.txt")
    assert response["Content-Type"].startswith("text/plain")
    text = response.content.decode()
    assert text.startswith("# HolidayOps\n\n> ")
    assert "support@ahmershah.dev" in text
    assert "](http://testserver/llms-full.txt)" in text
    assert "&quot;" not in text


def test_llms_full_lists_every_country_and_a_real_answer() -> None:
    text = Client().get("/llms-full.txt").content.decode()
    assert "- PK: Pakistan; weekend Saturday and Sunday;" in text
    assert "- SA: Saudi Arabia; weekend Friday and Saturday;" in text
    assert '"reason": "weekend"' in text
    assert "Authorization: Bearer" in text


def test_manifest_icons_exist() -> None:
    response = Client().get("/manifest.webmanifest")
    assert response["Content-Type"] == "application/manifest+json"
    data = json.loads(response.content)
    assert data["name"] == "HolidayOps"
    assert data["display"] == "standalone"
    assert any(icon.get("purpose") == "maskable" for icon in data["icons"])
    for icon in data["icons"]:
        assert finders.find(icon["src"].removeprefix("/static/"))


def test_service_worker_is_never_cached_and_skips_private_paths() -> None:
    response = Client().get("/sw.js")
    assert response["Content-Type"].startswith("text/javascript")
    assert response["Cache-Control"] == "no-cache"
    text = response.content.decode()
    assert 'const OFFLINE = "/offline/";' in text
    assert "&quot;" not in text
    # Only navigations and hashed static files are handled; everything else goes to the network.
    assert "const STATIC = /^\\/(static|assets)\\//;" in text


def test_offline_page_is_not_indexed() -> None:
    page = Client().get("/offline/").content.decode()
    assert '<meta name="robots" content="noindex">' in page
    assert 'rel="canonical"' not in page


def test_sitemap_lists_the_new_pages() -> None:
    pages = Client().get("/sitemap-pages.xml").content.decode()
    for path in ("/", "/about/", "/contact/", "/ur/about/"):
        assert f"<loc>http://testserver{path}</loc>" in pages
    legal = Client().get("/sitemap-legal.xml").content.decode()
    assert "<loc>http://testserver/privacy/</loc>" in legal
    assert "/ur/privacy/" not in legal
