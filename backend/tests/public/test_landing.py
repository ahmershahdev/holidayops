from datetime import date
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from apps.public.landing import demo, month_cells

YEAR = timezone.now().year


def test_landing_page_renders_in_every_language() -> None:
    for prefix, lang, direction in (("", "en", "ltr"), ("/ur", "ur", "rtl"), ("/ar", "ar", "rtl")):
        response = Client().get(f"{prefix}/")
        assert response.status_code == 200
        html = response.content.decode()
        assert f'<html lang="{lang}" dir="{direction}"' in html
        assert 'class="hero"' in html
        assert "landing.css" in html
        assert f'<link rel="canonical" href="http://testserver{prefix}/">' in html


def test_landing_allows_its_own_form_only() -> None:
    policy = Client().get("/")["Content-Security-Policy"]
    assert "form-action 'self'" in policy
    assert "script-src 'none'" in policy


def test_brand_links_home() -> None:
    assert 'class="brand" href="/ur/"' in Client().get("/ur/pricing/").content.decode()


def test_hero_calendar_is_this_month_with_holidays_and_weekends() -> None:
    today = date(YEAR, 3, 10)
    headers, weeks = month_cells("PK", "en", today)
    assert len(headers) == 7
    assert headers[0].weekday() == 0
    cells = [c for week in weeks for c in week]
    assert len(cells) % 7 == 0
    days = {c.day: c for c in cells if c.day}
    assert len(days) == 31
    assert "holiday" in days[date(YEAR, 3, 23)].kind
    assert "today" in days[today].kind
    weekend = {day.weekday() for day, c in days.items() if day and c.kind.startswith("weekend")}
    assert weekend <= {5, 6}


def test_saudi_calendar_starts_after_its_weekend() -> None:
    headers, _ = month_cells("SA", "ar", date(YEAR, 1, 15))
    assert headers[0].weekday() == 6


def test_demo_answers_and_validates() -> None:
    today = date(YEAR, 6, 1)
    assert demo({}, "en", today)[1] is None
    _, answer, error = demo({"country": "pk", "date": f"{YEAR}-03-23"}, "en", today)
    assert error == ""
    assert answer is not None
    assert (answer.working, answer.reason) == (False, "holiday")
    assert answer.names == ("Pakistan Day",)
    _, answer, _ = demo({"country": "PK", "date": f"{YEAR}-03-24"}, "en", today)
    assert answer is not None
    assert answer.working
    for params in (
        {"country": "XX", "date": f"{YEAR}-01-01"},
        {"country": "PK", "date": "nonsense"},
        {"country": "PK", "date": f"{YEAR + 20}-01-01"},
    ):
        values, answer, error = demo(params, "en", today)
        assert answer is None
        assert error
        assert values["country"] == params["country"].upper()


def test_demo_through_the_page() -> None:
    html = Client().get(f"/?country=PK&date={YEAR}-03-23").content.decode()
    assert 'class="demo-answer no"' in html
    assert "Pakistan Day" in html
    html = Client().get("/?country=ZZ&date=2026-01-01").content.decode()
    assert 'class="demo-answer error"' in html


def test_demo_queries_are_not_cached() -> None:
    cache.clear()
    Client().get(f"/?country=PK&date={YEAR}-03-23")
    Client().get("/")
    keys = list(getattr(cache, "_cache", {}).keys())
    assert any(":/" in str(k) and "?" not in str(k) for k in keys)
    assert not any("country=PK" in str(k) for k in keys)


def test_landing_shows_a_real_api_sample() -> None:
    html = Client().get("/").content.decode()
    assert "/api/v1/business-days/check/?country=PK" in html
    assert "&quot;is_business_day&quot;: false" in html


def test_root_is_the_landing_even_with_the_app_built(tmp_path: Path, settings: Any) -> None:
    settings.SPA_DIR = tmp_path
    (tmp_path / "index.html").write_text('<html data-theme="system">APP</html>')
    assert b"APP" not in Client().get("/").content
    assert b"APP" in Client().get("/playground").content


@pytest.mark.parametrize(
    "path", ["/ur/?country=PK&date=2026-03-23", "/ar/?country=SA&date=2026-09-23"]
)
def test_rtl_demo_answers(path: str) -> None:
    response = Client().get(path)
    assert response.status_code == 200
    assert 'class="demo-answer' in response.content.decode()
