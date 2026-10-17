"""The palette lives in two stylesheets (the web app's Tailwind theme and the public pages);
they must stay identical in both themes and pass WCAG AA. Design: docs/design/m6-showcase.md."""

from pathlib import Path

import pytest

from apps.public.palette import contrast, theme_tokens

ROOT = Path(__file__).resolve().parents[3]
APP_CSS = (ROOT / "frontend" / "src" / "index.css").read_text(encoding="utf-8")
PUBLIC_CSS = (ROOT / "backend" / "apps" / "public" / "static" / "public" / "site.css").read_text(
    encoding="utf-8"
)

LIGHT = theme_tokens(PUBLIC_CSS, ":root")
DARK = theme_tokens(PUBLIC_CSS, ':root[data-theme="dark"]')

TEXT_PAIRS = [
    ("ink", "paper"),
    ("ink", "surface"),
    ("muted", "paper"),
    ("muted", "surface"),
    ("accent", "surface"),
    ("accent", "paper"),
    ("on-accent", "accent"),
    ("on-accent", "accent-strong"),
    ("accent-strong", "accent-soft"),
    ("holiday", "holiday-soft"),
    ("closure", "closure-soft"),
    ("halfday", "halfday-soft"),
    ("workday", "workday-soft"),
    ("muted", "weekend"),
]


def app_tokens(css: str, selector: str) -> dict[str, str]:
    return {k.removeprefix("color-"): v for k, v in theme_tokens(css, selector).items()}


def test_app_and_public_light_palettes_match() -> None:
    app = app_tokens(APP_CSS, "@theme")
    assert app
    assert {name: LIGHT.get(name) for name in app} == app


def test_app_and_public_dark_palettes_match() -> None:
    assert app_tokens(APP_CSS, ':root[data-theme="dark"]') == DARK


def test_system_dark_repeats_the_dark_theme() -> None:
    public_media = PUBLIC_CSS[PUBLIC_CSS.index("@media (prefers-color-scheme: dark)") :]
    assert theme_tokens(public_media, ':root[data-theme="system"]') == DARK
    app_media = APP_CSS[APP_CSS.index("@media (prefers-color-scheme: dark)") :]
    assert app_tokens(app_media, ':root[data-theme="system"]') == DARK


def test_logo_colours_are_the_brand_anchors() -> None:
    assert LIGHT["ink"] == "#0b1b3f"
    assert LIGHT["glow"] == "#00b3a6"


def test_contrast_ratio_matches_wcag() -> None:
    assert contrast("#000000", "#ffffff") == 21.0
    assert contrast("#ffffff", "#ffffff") == 1.0
    assert contrast("#0b1b3f", "#f7fafc") == 16.12


@pytest.mark.parametrize("tokens", [LIGHT, DARK], ids=["light", "dark"])
def test_every_text_pair_passes_aa(tokens: dict[str, str]) -> None:
    for fg, bg in TEXT_PAIRS:
        assert contrast(tokens[fg], tokens[bg]) >= 4.5, (fg, bg)
    assert contrast(tokens["accent"], tokens["paper"]) >= 3, "scrollbar thumb on track"


def test_footer_text_passes_on_both_night_colours() -> None:
    for night in (LIGHT["night"], DARK["night"]):
        for text in ("#c7d3e3", "#e6edf7", "#8fa3bd", "#a3b3c9", "#2dd4c4"):
            assert contrast(text, night) >= 4.5, (text, night)
