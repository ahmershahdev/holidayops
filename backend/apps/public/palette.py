import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

SITE_CSS = Path(__file__).resolve().parent / "static" / "public" / "site.css"
_TOKEN = re.compile(r"--([a-z-]+):\s*(#[0-9a-f]{6});", re.IGNORECASE)


@dataclass(frozen=True)
class Swatch:
    name: str
    hex: str
    on_surface: float
    on_night: float


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    """WCAG 2 contrast ratio between two #rrggbb colours."""
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return round((high + 0.05) / (low + 0.05), 2)


def theme_tokens(css: str, selector: str) -> dict[str, str]:
    """The colour tokens declared in the first block whose selector is exactly `selector`."""
    start = css.index(selector + " {")
    block = css[start : css.index("}", start)]
    return dict(_TOKEN.findall(block))


@cache
def swatches() -> tuple[Swatch, ...]:
    tokens = theme_tokens(SITE_CSS.read_text(encoding="utf-8"), ":root")
    surface, night = tokens["surface"], tokens["night"]
    return tuple(
        Swatch(name, value.lower(), contrast(value, surface), contrast(value, night))
        for name, value in tokens.items()
    )
