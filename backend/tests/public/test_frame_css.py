"""The footer is styled by one block pasted into both stylesheets; it must not drift."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STYLESHEETS = [
    ROOT / "backend" / "apps" / "public" / "static" / "public" / "site.css",
    ROOT / "frontend" / "src" / "index.css",
]
BLOCK = re.compile(r"/\* frame:footer .*?/\* end frame:footer \*/", re.S)


def footer_block(path: Path) -> str:
    css = path.read_text(encoding="utf-8")
    assert len(BLOCK.findall(css)) == 1, path
    match = BLOCK.search(css)
    assert match
    return match.group(0)


def test_footer_block_is_identical_in_both_stylesheets() -> None:
    public, app = (footer_block(path) for path in STYLESHEETS)
    assert public == app


SHARED_CLASSES = [
    "footer-cta-title",
    "footer-route",
    "footer-grid",
    "footer-countries",
    "to-top",
    "footer-word",
]


def test_footer_markup_uses_the_shared_classes() -> None:
    template = ROOT / "backend/apps/public/templates/public/_footer.html"
    component = ROOT / "frontend/src/components/frame/SiteFooter.tsx"
    for path in (template, component):
        markup = path.read_text(encoding="utf-8")
        for name in SHARED_CLASSES:
            assert name in markup, (path.name, name)
