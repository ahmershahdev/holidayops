from pathlib import Path
from typing import Any

import pytest
from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import path


def test_theme_switch_sets_the_cookie_and_returns() -> None:
    web = Client()
    response = web.get("/theme/dark/?next=/holidays/pk/2026/")
    assert response.status_code == 302
    assert response["Location"] == "/holidays/pk/2026/"
    cookie = response.cookies["theme"]
    assert cookie.value == "dark"
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/"
    cleared = web.get("/theme/system/?next=/pricing/")
    assert cleared.cookies["theme"].value == ""


def test_theme_switch_never_redirects_off_site() -> None:
    for target in ("https://evil.example/", "//evil.example/", "/\\evil.example"):
        assert Client().get(f"/theme/dark/?next={target}")["Location"] == "/"


def test_pages_render_the_chosen_theme_and_cache_one_copy_per_theme() -> None:
    web = Client()
    assert 'data-theme="system"' in web.get("/pricing/").content.decode()
    web.cookies["theme"] = "dark"
    dark = web.get("/pricing/")
    assert 'data-theme="dark"' in dark.content.decode()
    assert '<meta name="color-scheme" content="dark">' in dark.content.decode()
    web.cookies["theme"] = "light"
    assert 'data-theme="light"' in web.get("/pricing/").content.decode()
    web.cookies["theme"] = "nonsense"
    assert 'data-theme="system"' in web.get("/pricing/").content.decode()


def test_html_is_revalidated_and_varies_by_cookie() -> None:
    response = Client().get("/holidays/")
    assert response["Cache-Control"] == "no-cache"
    assert "Cookie" in response["Vary"]


def test_header_and_footer_are_on_every_page() -> None:
    html = Client().get("/ar/pricing/").content.decode()
    assert 'class="site-header"' in html
    assert 'class="site-footer"' in html
    assert 'href="/theme/dark/?next=/ar/pricing/"' in html
    assert 'class="nav-mobile"' in html
    assert 'href="/ar/holidays/pk/' in html


@pytest.mark.parametrize("path", ["/no-such-page/", "/holidays/xx/2026/", "/ur/nothing/"])
def test_broken_urls_get_the_branded_404(path: str) -> None:
    response = Client().get(path)
    assert response.status_code == 404
    html = response.content.decode()
    assert 'class="error-code"' in html
    assert '<meta name="robots" content="noindex">' in html
    assert response["Content-Security-Policy"].startswith("default-src 'none'")


def test_urdu_404_is_in_urdu() -> None:
    html = Client().get("/ur/nothing/").content.decode()
    assert '<html lang="ur" dir="rtl"' in html
    assert "This flight went off course" not in html


def test_api_404_stays_json() -> None:
    response = Client().get("/api/v1/nothing-here/")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


def boom(request: Any) -> HttpResponse:
    raise RuntimeError("boom")


urlpatterns = [path("boom/", boom), path("api/boom/", boom)]
handler500 = "config.errors.server_error"


@override_settings(ROOT_URLCONF=__name__, DEBUG=False)
def test_server_errors_render_a_static_500_page() -> None:
    web = Client(raise_request_exception=False)
    page = web.get("/boom/")
    assert page.status_code == 500
    assert b"Something went wrong" in page.content
    api = web.get("/api/boom/")
    assert api.status_code == 500
    assert api.json() == {"detail": "Server error."}


def test_spa_gets_the_saved_theme(tmp_path: Path, settings: Any) -> None:
    settings.SPA_DIR = tmp_path
    (tmp_path / "index.html").write_text('<html lang="en" dir="ltr" data-theme="system">')
    web = Client()
    web.cookies["theme"] = "dark"
    assert b'data-theme="dark"' in web.get("/app").content
