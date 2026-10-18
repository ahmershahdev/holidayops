import calendar
from datetime import UTC, date, datetime

import pytest
from django.test import Client
from django.utils import timezone

from apps.core import list_countries
from apps.public.overlap import overlap, parse
from apps.public.today import country_today, country_zone, local_today, world_today

YEAR = timezone.now().year


def test_zones_use_the_capital_for_wide_countries() -> None:
    assert country_zone("US").key == "America/New_York"
    assert country_zone("PK").key == "Asia/Karachi"
    assert country_zone("BV").key == "UTC"


def test_today_is_the_local_date() -> None:
    late = datetime(YEAR, 3, 22, 21, 0, tzinfo=UTC)
    assert local_today("PK", late) == date(YEAR, 3, 23)
    assert local_today("US", late) == date(YEAR, 3, 22)


def test_country_today_on_pakistan_day() -> None:
    page = country_today(list_countries()["PK"], "en", date(YEAR, 3, 23))
    assert not page.today.working
    assert page.today.names == ("Pakistan Day",)
    assert len(page.week) == 7
    assert page.next_working > page.today.day
    assert page.next_holiday is not None
    assert page.next_holiday.day > page.today.day


def test_world_today_puts_every_country_in_one_group() -> None:
    world = world_today("en", datetime(YEAR, 3, 23, 9, 0, tzinfo=UTC))
    groups = [world.holiday, world.weekend, world.working]
    codes = [row.code for group in groups for row in group]
    assert sorted(codes) == sorted(list_countries())
    assert "PK" in [row.code for row in world.holiday]


@pytest.mark.parametrize("path", ["/today/", "/holidays/pk/today/", "/ar/holidays/sa/today/"])
def test_today_pages_render(path: str) -> None:
    response = Client().get(path)
    assert response.status_code == 200
    assert 'class="crumbs"' in response.content.decode()


def test_country_today_404s_for_unknown_countries() -> None:
    assert Client().get("/holidays/zz/today/").status_code == 404


def test_widget_can_be_framed_anywhere_and_follows_language() -> None:
    response = Client().get("/widget/sa/?lang=ar&theme=dark")
    assert response.status_code == 200
    assert "frame-ancestors *" in response["Content-Security-Policy"]
    assert "X-Frame-Options" not in response
    html = response.content.decode()
    assert '<html lang="ar" dir="rtl" data-theme="dark">' in html
    assert 'target="_blank" rel="noopener"' in html
    assert "<script" not in html


def test_widget_ignores_unknown_options() -> None:
    html = Client().get("/widget/pk/?lang=fr&theme=neon").content.decode()
    assert '<html lang="en" dir="ltr" data-theme="light">' in html
    assert Client().get("/widget/zz/").status_code == 404


def test_overlap_counts_every_day_once() -> None:
    first = date(YEAR, 3, 1)
    result = overlap(["PK", "SA"], first, "en")
    days = calendar.monthrange(YEAR, 3)[1]
    assert result.shared + result.partial + result.closed == days
    pakistan_day = next(
        cell for week in result.weeks for cell in week if cell.day == date(YEAR, 3, 23)
    )
    assert "PK" in [off.code for off in pakistan_day.off]
    assert [c[0] for c in result.countries] == ["PK", "SA"]


def test_overlap_input_is_validated() -> None:
    today = date(YEAR, 6, 1)
    assert parse([], "", today) == (["PK", "SA", "GB"], date(YEAR, 6, 1), "")
    assert parse(["pk", "PK", "sa"], f"{YEAR}-02", today)[:2] == (["PK", "SA"], date(YEAR, 2, 1))
    assert parse(["PK"], "", today)[2]
    assert parse(["PK", "XX"], "", today)[2]
    assert parse(["PK", "SA"], "nonsense", today)[2]
    assert parse(["PK", "SA"], f"{YEAR + 20}-01", today)[2]
    assert len(parse(["PK", "SA", "GB", "US", "IN"], "", today)[0]) == 4


def test_overlap_page_allows_its_own_form() -> None:
    response = Client().get(f"/tools/overlap/?c=PK&c=SA&month={YEAR}-03")
    assert response.status_code == 200
    assert "form-action 'self'" in response["Content-Security-Policy"]
    assert "Pakistan Day" in response.content.decode()


def test_sitemap_lists_today_pages() -> None:
    xml = Client().get("/sitemap-pk.xml").content.decode()
    assert "<loc>http://testserver/holidays/pk/today/</loc>" in xml
    pages = Client().get("/sitemap-pages.xml").content.decode()
    assert "<loc>http://testserver/tools/overlap/</loc>" in pages
