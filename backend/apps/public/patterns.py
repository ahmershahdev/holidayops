"""Each country's geometric banner (docs/design/m6-showcase.md, 6.3): a grid of tiles whose motifs,
turns and gaps come from a hash of the code, coloured from the country's own flag."""

import hashlib
import random
import re
from collections import Counter
from dataclasses import dataclass
from functools import cache

from apps.public.flags import FLAG_DIR
from apps.public.palette import contrast

COLS, ROWS, TILE = 20, 4, 40
NIGHT = "#0b1b3f"
BRAND = ("#2dd4c4", "#e6edf7")
MOTIFS = {
    "quarter": "M0 40A40 40 0 0 1 40 0V40Z",
    "half": "M0 40a20 20 0 0 1 40 0Z",
    "triangle": "M0 40H40L0 0Z",
    "dot": "M20 8a12 12 0 1 1 0 24a12 12 0 1 1 0-24Z",
    "bar": "M0 14H40V26H0Z",
    "star": "M20 0L26 14L40 20L26 26L20 40L14 26L0 20L14 14Z",
}
_COLOUR = re.compile(r'(?:fill|stop-color)="(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|[a-z]+)"')
# The only named colours flag-icons uses.
NAMED = {
    "red": "#ff0000",
    "gold": "#ffd700",
    "gray": "#808080",
    "green": "#008000",
    "purple": "#800080",
}


@dataclass(frozen=True)
class Tile:
    motif: str
    x: int
    y: int
    turn: int
    colour: str


@dataclass(frozen=True)
class Pattern:
    code: str
    motifs: tuple[str, ...]
    rows: tuple[tuple[Tile, ...], ...]
    width: int = COLS * TILE
    height: int = ROWS * TILE

    @property
    def defs(self) -> list[tuple[str, str]]:
        return [(name, MOTIFS[name]) for name in self.motifs]


def _full(value: str) -> str:
    h = NAMED.get(value, value.lower())
    return "#" + "".join(c * 2 for c in h[1:]) if len(h) == 4 else h


def _distance(a: str, b: str) -> int:
    return sum(abs(int(a[i : i + 2], 16) - int(b[i : i + 2], 16)) for i in (1, 3, 5))


@cache
def flag_colours(code: str) -> tuple[str, ...]:
    """The flag's most used colours that stand out on the night panel, at most four."""
    path = FLAG_DIR / f"{code.lower()}.svg"
    text = path.read_text(encoding="utf-8")
    found = Counter(_full(c) for c in _COLOUR.findall(text) if c.startswith("#") or c in NAMED)
    picked: list[str] = []
    for colour, _n in found.most_common():
        if contrast(colour, NIGHT) < 1.8 or any(_distance(colour, p) < 60 for p in picked):
            continue
        picked.append(colour)
        if len(picked) == 4:
            break
    return tuple(picked + [c for c in BRAND if c not in picked][: max(0, 2 - len(picked))])


@cache
def pattern(code: str) -> Pattern:
    seed = int.from_bytes(hashlib.sha256(code.upper().encode()).digest()[:8])
    rng = random.Random(seed)  # noqa: S311 - decoration that must repeat, not a secret
    motifs = tuple(rng.sample(sorted(MOTIFS), 3))
    colours = flag_colours(code)
    density = rng.uniform(0.55, 0.8)
    rows = tuple(
        tuple(
            Tile(
                rng.choice(motifs),
                col * TILE,
                row * TILE,
                rng.choice((0, 90, 180, 270)),
                rng.choice(colours),
            )
            for col in range(COLS)
            if rng.random() < density
        )
        for row in range(ROWS)
    )
    return Pattern(code.lower(), motifs, rows)
