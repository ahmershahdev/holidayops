import pytest
from django.test import Client

from apps.core import list_countries
from apps.public.flags import FLAG_DIR, UnsafeSvg, sanitize
from config.csp import STATIC_SVG_POLICY, static_headers

NS = 'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'


def svg(body: str, attrs: str = "") -> str:
    return f'<svg {NS} viewBox="0 0 4 3"{attrs}>{body}</svg>'


def test_every_country_has_a_flag() -> None:
    missing = [c for c in list_countries() if not (FLAG_DIR / f"{c.lower()}.svg").is_file()]
    assert missing == []


def test_the_mit_notice_ships_with_the_flags() -> None:
    notice = (FLAG_DIR / "LICENSE.txt").read_text(encoding="utf-8")
    assert "The MIT License" in notice
    assert "Copyright (c) 2013 Panayiotis Lipiridis" in notice


def test_committed_flags_are_already_sanitised() -> None:
    for path in FLAG_DIR.glob("*.svg"):
        text = path.read_text(encoding="utf-8")
        assert sanitize(text) == text, path.name


@pytest.mark.parametrize(
    "source",
    [
        svg("<script>alert(1)</script>"),
        svg('<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">x</div></foreignObject>'),
        svg('<image href="https://evil.example/x.png"/>'),
        svg('<animate attributeName="href" to="javascript:alert(1)"/>'),
        svg('<use xlink:href="https://evil.example/s.svg#a"/>'),
        svg('<use href="data:image/svg+xml;base64,PHN2Zz4="/>'),
        svg('<path fill="url(https://evil.example/p)" d="M0 0h1"/>'),
        svg('<path style="fill:url(//evil.example/p)" d="M0 0h1"/>'),
        '<!DOCTYPE svg [<!ENTITY a "aaaa">]>' + svg("<g>&a;</g>"),
        '<?xml-stylesheet href="https://evil.example/s.css"?>' + svg("<g/>"),
        '<html xmlns="http://www.w3.org/1999/xhtml"/>',
    ],
)
def test_unsafe_svg_is_refused(source: str) -> None:
    with pytest.raises(UnsafeSvg):
        sanitize(source)


def test_unknown_attributes_and_styles_are_dropped() -> None:
    clean = sanitize(
        svg(
            '<path onclick="alert(1)" class="x" style="fill:red;behavior:url(#a);position:fixed" '
            'd="M0 0h1"/><use xlink:href="#p"/>',
            ' id="flag-icons-xx" onload="alert(1)"',
        )
    )
    assert "onclick" not in clean
    assert "onload" not in clean
    assert "class" not in clean
    assert "position" not in clean
    assert "behavior" not in clean
    assert "flag-icons" not in clean
    assert 'style="fill:red"' in clean
    assert 'xlink:href="#p"' in clean


def test_static_svgs_get_their_own_policy() -> None:
    headers: dict[str, str] = {}
    static_headers(headers, "/app/staticfiles/public/flags/pk.abc123.svg", "/static/x.svg")
    assert headers == {"Content-Security-Policy": STATIC_SVG_POLICY}
    other: dict[str, str] = {}
    static_headers(other, "/app/staticfiles/public/site.css", "/static/site.css")
    assert other == {}


@pytest.mark.django_db
def test_country_list_and_page_show_decorative_flags(client: Client) -> None:
    listing = client.get("/holidays/").content.decode()
    assert '<img class="flag" src="/static/public/flags/pk.svg" alt=""' in listing
    assert listing.count('class="flag"') == len(list_countries())
    assert 'loading="lazy"' in listing
    page = client.get("/ur/holidays/pk/2026/").content.decode()
    assert (
        '<h1 class="title-flag"><img class="flag" src="/static/public/flags/pk.svg" alt=""' in page
    )
    assert 'width="48" height="36" loading="eager"' in page
