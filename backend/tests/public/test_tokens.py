"""The palette lives in two stylesheets (the web app's Tailwind theme and the public pages);
they must stay identical. Design: docs/design/m6-showcase.md."""

import re
from pathlib import Path

from apps.public.palette import contrast, swatches

ROOT = Path(__file__).resolve().parents[3]
APP_CSS = ROOT / "frontend" / "src" / "index.css"
PUBLIC_CSS = ROOT / "backend" / "apps" / "public" / "static" / "public" / "site.css"


def colors(text: str, prefix: str) -> dict[str, str]:
    pattern = rf"--{prefix}([a-z-]+):\s*(#[0-9a-f]{{6}});"
    return dict(re.findall(pattern, text, re.IGNORECASE))


def test_app_and_public_palettes_match() -> None:
    app = colors(APP_CSS.read_text(encoding="utf-8"), "color-")
    public = colors(PUBLIC_CSS.read_text(encoding="utf-8"), "")
    assert app, "no colour tokens found in the app stylesheet"
    assert {name: public.get(name) for name in app} == app


def test_logo_colours_are_the_brand_anchors() -> None:
    app = colors(APP_CSS.read_text(encoding="utf-8"), "color-")
    assert app["ink"] == "#0b1b3f"
    assert app["glow"] == "#00b3a6"


def test_contrast_ratio_matches_wcag() -> None:
    assert contrast("#000000", "#ffffff") == 21.0
    assert contrast("#ffffff", "#ffffff") == 1.0
    assert contrast("#0b1b3f", "#f7fafc") == 16.12


def test_every_text_token_passes_aa_on_its_background() -> None:
    tokens = {s.name: s.hex for s in swatches()}
    pairs = [
        ("ink", "paper"),
        ("muted", "paper"),
        ("accent", "surface"),
        ("accent-strong", "accent-soft"),
        ("holiday", "holiday-soft"),
        ("closure", "closure-soft"),
        ("halfday", "halfday-soft"),
        ("workday", "workday-soft"),
    ]
    for fg, bg in pairs:
        assert contrast(tokens[fg], tokens[bg]) >= 4.5, (fg, bg)
    assert contrast("#ffffff", tokens["accent"]) >= 4.5
    assert contrast("#ffffff", tokens["accent-strong"]) >= 4.5
