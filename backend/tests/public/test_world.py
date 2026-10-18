from datetime import date

from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from apps.core import list_countries
from apps.public.world import UPCOMING_LIMIT, UPCOMING_PER_DAY, build_world, world

YEAR = timezone.now().year


def test_pakistan_day_is_a_holiday_today() -> None:
    snapshot = build_world(date(YEAR, 3, 23), "en")
    codes = [p.code for p in snapshot.holiday_today]
    assert "PK" in codes
    assert codes == [p.code for p in sorted(snapshot.holiday_today, key=lambda p: p.name)]
    pk = next(p for p in snapshot.holiday_today if p.code == "PK")
    assert pk.path == f"/holidays/pk/{YEAR}/"


def test_weekends_cover_every_country_most_common_first() -> None:
    snapshot = build_world(date(YEAR, 3, 23), "en")
    counts = [g.count for g in snapshot.weekends]
    assert sum(counts) == len(list_countries())
    assert counts == sorted(counts, reverse=True)
    assert snapshot.weekends[0].days == (5, 6)
    fri_sat = next(g for g in snapshot.weekends if g.days == (4, 5))
    assert fri_sat.examples[0].code == "SA"
    assert len(fri_sat.examples) <= 4


def test_upcoming_is_spread_over_days_and_in_order() -> None:
    today = date(YEAR, 3, 20)
    upcoming = build_world(today, "en").upcoming
    assert 0 < len(upcoming) <= UPCOMING_LIMIT
    days = [u.day for u in upcoming]
    assert days == sorted(days)
    assert all(today < d for d in days)
    assert all(days.count(d) <= UPCOMING_PER_DAY for d in days)
    assert all(u.names for u in upcoming)


def test_snapshot_is_cached_per_day_and_language() -> None:
    cache.clear()
    first = world(date(YEAR, 3, 23), "ur")
    assert world(date(YEAR, 3, 23), "ur") is not None
    assert cache.get(f"world:{YEAR}-03-23:ur") == first


def test_landing_shows_the_live_sections() -> None:
    page = Client().get("/").content.decode()
    for part in ('id="today"', 'class="weekend-table"', 'class="faq"', 'class="eyebrow live"'):
        assert part in page
