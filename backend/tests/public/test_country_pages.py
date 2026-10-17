import re

import pytest
from django.test import Client
from django.utils import timezone

from apps.core import list_countries
from apps.public.content import country_name, join_list
from apps.public.palette import contrast
from apps.public.patterns import COLS, NIGHT, ROWS, flag_colours, pattern

pytestmark = pytest.mark.django_db

YEAR = timezone.now().year
ARABIC_COMMA = "،"


def page(client: Client, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200
    return response.content.decode()


@pytest.mark.parametrize(
    ("lang", "expected"),
    [("en", "Pakistan"), ("ur", "پاکستان"), ("ar", "باكستان")],
)
def test_country_names_follow_the_page_language(lang: str, expected: str) -> None:
    assert country_name("PK", lang) == expected


def test_every_country_has_a_name_in_every_language() -> None:
    for code in list_countries():
        for lang in ("ur", "ar"):
            assert country_name(code, lang) != list_countries()[code].name, (code, lang)


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("en", "Friday and Saturday"),
        ("ur", "جمعہ اور ہفتہ"),
        ("ar", "الجمعة والسبت"),
    ],
)
def test_lists_use_each_language_pattern(lang: str, expected: str) -> None:
    days = {"en": ("Friday", "Saturday"), "ur": ("جمعہ", "ہفتہ"), "ar": ("الجمعة", "السبت")}
    assert join_list(days[lang], lang) == expected


def test_longer_lists_use_each_script_own_punctuation() -> None:
    assert join_list(("ب", "ج", "د"), "ur") == f"ب{ARABIC_COMMA} ج{ARABIC_COMMA} اور د"
    assert join_list(("أ", "ب", "ج"), "ar") == "أ وب وج"


@pytest.mark.parametrize(
    ("path", "weekend", "name"),
    [
        (f"/ar/holidays/sa/{YEAR}/", "الجمعة والسبت", "المملكة العربية السعودية"),
        (f"/ur/holidays/sa/{YEAR}/", "جمعہ اور ہفتہ", "سعودی عرب"),
        (f"/holidays/sa/{YEAR}/", "Friday and Saturday", "Saudi Arabia"),
    ],
)
def test_country_page_weekend_and_name_are_localised(
    client: Client, path: str, weekend: str, name: str
) -> None:
    html = page(client, path)
    assert f"<strong>{weekend}</strong>" in html
    heading = html.split('<h1 class="title-flag">', 1)[1].split("</h1>", 1)[0]
    assert name in heading
    assert re.search(r"<strong>[^<]*, [^<]*</strong>", html) is None


def test_country_page_has_banner_calendar_and_accessible_table(client: Client) -> None:
    html = page(client, f"/holidays/pk/{YEAR}/")
    assert '<div class="pattern" aria-hidden="true">' in html
    assert '<section class="year-cal" aria-hidden="true">' in html
    assert html.count('<div class="month reveal">') == 12
    assert html.count('class="cal-cell holiday') >= 5
    assert "<table>" in html
    assert 'title="Pakistan Day"' in html


def test_patterns_are_stable_and_distinct() -> None:
    assert pattern("PK") == pattern("pk")
    assert pattern("PK") != pattern("SA")
    tiles = [t for row in pattern("PK").rows for t in row]
    assert 0.4 * COLS * ROWS < len(tiles) <= COLS * ROWS


def test_pattern_colours_come_from_the_flag_and_show_on_the_panel() -> None:
    assert "#ffffff" in flag_colours("PK")
    assert "#ff0000" in flag_colours("DE")
    for code in list_countries():
        colours = flag_colours(code)
        assert 2 <= len(colours) <= 4, code
        assert all(contrast(c, NIGHT) >= 1.8 for c in colours), code


def test_month_headers_carry_short_and_narrow_cldr_names(client: Client) -> None:
    html = page(client, f"/ar/holidays/sa/{YEAR}/")
    assert '<span class="day-short">أحد</span><span class="day-narrow">ح</span>' in html
    urdu = page(client, f"/ur/holidays/pk/{YEAR}/")
    assert '<span class="day-short">ہفتہ</span>' in urdu
    assert "ھفتہ" not in urdu
