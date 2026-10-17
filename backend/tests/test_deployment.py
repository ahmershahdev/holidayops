import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from django.test import Client
from rest_framework.test import APIClient

from apps.api import views as api_views
from config.spa import SPA_POLICY
from tests.factories import CalendarFactory, MembershipFactory, SourceFactory

BACKEND = Path(__file__).resolve().parents[1]


@pytest.mark.django_db
def test_healthz_reports_database_and_cache() -> None:
    response = Client().get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "cache": "ok"}
    assert "no-cache" in response["Cache-Control"]


@pytest.mark.django_db
def test_healthz_answers_probes_that_use_an_ip_as_host() -> None:
    assert Client().get("/healthz", HTTP_HOST="10.0.0.7:8000").status_code == 200
    assert Client().get("/holidays/", HTTP_HOST="10.0.0.7:8000").status_code == 400


@pytest.mark.django_db
def test_healthz_is_503_when_a_dependency_is_down() -> None:
    with mock.patch("config.health.cache.set", side_effect=ConnectionError("redis down")):
        response = Client().get("/healthz")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "ok", "cache": "error"}
    with mock.patch("config.health.connection.cursor", side_effect=OSError("db down")):
        assert Client().get("/healthz").json()["database"] == "error"


def test_spa_routes_serve_the_built_index(tmp_path: Path, settings: Any) -> None:
    settings.SPA_DIR = tmp_path
    (tmp_path / "index.html").write_text("<!doctype html><title>HolidayOps</title>")
    for path in (
        "/playground",
        "/login",
        "/signup",
        "/invite",
        "/unsubscribe",
        "/app",
        "/app/acme/x",
    ):
        response = Client().get(path)
        assert response.status_code == 200, path
        assert b"<title>HolidayOps</title>" in response.content
        assert response["Cache-Control"] == "no-cache"
        assert response["Content-Security-Policy"] == SPA_POLICY
    assert Client().get("/apps").status_code == 404


def test_spa_routes_are_404_when_the_app_is_not_built(tmp_path: Path, settings: Any) -> None:
    settings.SPA_DIR = tmp_path
    assert Client().get("/login").status_code == 404


@pytest.mark.django_db
def test_country_holiday_lists_are_cached_by_query() -> None:
    url = "/api/v1/holidays/?country=PK&year=2027"
    with mock.patch.object(
        api_views.HolidayListView, "_build", autospec=True, side_effect=lambda *a: {"n": 1}
    ) as build:
        assert APIClient().get(url).data == {"n": 1}
        assert APIClient().get(url).data == {"n": 1}
        APIClient().get(url + "&categories=public")
    assert build.call_count == 2


@pytest.mark.django_db
def test_cached_list_matches_a_fresh_one() -> None:
    url = "/api/v1/holidays/?country=PK&year=2027&language=ur_PK"
    first = APIClient().get(url).data
    assert APIClient().get(url).data == first
    assert any(h["name"] == "یوم پاکستان" for h in first["holidays"])


@pytest.mark.django_db
def test_company_calendar_lists_are_never_cached(client_for: Any) -> None:
    member = MembershipFactory.create()
    calendar = CalendarFactory.create(org=member.org)
    SourceFactory.create(calendar=calendar)
    api = client_for(member.user)
    url = f"/api/v1/holidays/?calendar={calendar.id}&year=2027"
    before = api.get(url).data["holidays"]
    calendar.custom_days.create(date="2027-04-05", name="Office move", kind="closure")
    after = api.get(url).data["holidays"]
    assert len(after) == len(before) + 1


def test_production_settings() -> None:
    script = (
        "import json, django; from django.conf import settings; django.setup();"
        "print(json.dumps({'mw': settings.MIDDLEWARE, 'db': settings.DATABASES['default'],"
        "'redirect': settings.SECURE_SSL_REDIRECT, 'hsts': settings.SECURE_HSTS_SECONDS,"
        "'static': settings.STORAGES['staticfiles']['BACKEND'],"
        "'root': str(settings.WHITENOISE_ROOT)}, default=str))"
    )
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "DJANGO_SECRET_KEY": "x",
        "REDIS_URL": "redis://localhost:6379/0",
        "MYSQL_SSL_MODE": "REQUIRED",
        "MYSQL_SSL_CA": "/etc/ssl/certs/ca-certificates.crt",
    }
    out = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    conf = json.loads(out.stdout)
    assert conf["mw"][:3] == [
        "config.health.HealthCheckMiddleware",
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",
    ]
    assert conf["db"]["OPTIONS"]["ssl_mode"] == "REQUIRED"
    assert conf["db"]["OPTIONS"]["ssl"] == {"ca": "/etc/ssl/certs/ca-certificates.crt"}
    assert conf["db"]["CONN_MAX_AGE"] == 60
    assert conf["redirect"] is True
    assert conf["hsts"] == 63072000
    assert conf["static"].startswith("whitenoise.")
    assert conf["root"].endswith("spa")


def test_test_settings_are_untouched_by_production_settings() -> None:
    from django.conf import settings

    assert "whitenoise.middleware.WhiteNoiseMiddleware" not in settings.MIDDLEWARE
    assert "ssl_mode" not in settings.DATABASES["default"]["OPTIONS"]
