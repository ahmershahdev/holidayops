from pathlib import Path
from typing import Any

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from apps.public import views
from config.errors import BrandedNotFoundMiddleware

pytestmark = pytest.mark.django_db


def technical_404(request: HttpRequest) -> HttpResponse:
    return HttpResponse("<h1>Page not found at /x/</h1>", status=404, content_type="text/html")


def test_development_404s_get_the_branded_page(settings: Any) -> None:
    settings.DEBUG = True
    response = BrandedNotFoundMiddleware(technical_404)(RequestFactory().get("/holidays/2/"))
    assert response.status_code == 404
    assert "This flight went off course" in response.content.decode()


def test_api_404s_stay_json_in_development(settings: Any) -> None:
    settings.DEBUG = True
    response = BrandedNotFoundMiddleware(technical_404)(RequestFactory().get("/api/v1/nope/"))
    assert response.content.decode() == "<h1>Page not found at /x/</h1>"


def test_page_cache_key_changes_with_each_static_build(tmp_path: Path, settings: Any) -> None:
    settings.STATIC_ROOT = tmp_path
    views.build_id.cache_clear()
    assert views.build_id() == "dev"
    (tmp_path / "staticfiles.json").write_text('{"paths": {"public/site.css": "site.1.css"}}')
    views.build_id.cache_clear()
    first = views.build_id()
    (tmp_path / "staticfiles.json").write_text('{"paths": {"public/site.css": "site.2.css"}}')
    views.build_id.cache_clear()
    assert views.build_id() not in {first, "dev"}
    views.build_id.cache_clear()


def test_only_private_app_routes_are_noindex(tmp_path: Path, settings: Any, client: Any) -> None:
    settings.SPA_DIR = tmp_path
    (tmp_path / "index.html").write_text('<html data-theme="system"><head></head></html>')
    assert "noindex" in client.get("/app").content.decode()
    assert "noindex" not in client.get("/playground").content.decode()
