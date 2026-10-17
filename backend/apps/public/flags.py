"""Country flags: SVGs from flag-icons 7.5.0 (MIT, https://github.com/lipis/flag-icons), cleaned
by `sanitize` when imported (`manage.py import_flags`) and served as static files."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from django.templatetags.static import static

FLAG_DIR = Path(__file__).resolve().parent / "static" / "public" / "flags"

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)

ELEMENTS = {
    "svg", "g", "defs", "path", "rect", "circle", "ellipse", "line", "polygon", "polyline",
    "use", "clipPath", "mask", "marker", "linearGradient", "radialGradient", "stop",
}  # fmt: skip
ATTRIBUTES = {
    "viewBox", "width", "height", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry",
    "fx", "fy", "d", "points", "transform", "id", "fill", "fill-rule", "fill-opacity", "stroke",
    "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "stroke-opacity",
    "stroke-dasharray", "opacity", "clip-path", "clip-rule", "mask", "offset", "stop-color",
    "stop-opacity", "gradientUnits", "gradientTransform", "spreadMethod", "clipPathUnits",
    "maskUnits", "markerWidth", "markerHeight", "refX", "refY", "orient", "markerUnits",
    "overflow", "color", "preserveAspectRatio", "href", "marker-start", "marker-mid",
    "marker-end", "vector-effect",
}  # fmt: skip
STYLE_PROPERTIES = ATTRIBUTES - {"d", "id", "href", "transform"}

_URL = re.compile(r"url\(\s*([^)]*)\)")
_LOCAL_URL = re.compile(r"#[\w.-]+")


class UnsafeSvg(ValueError):
    pass


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _check_urls(value: str) -> str:
    for target in _URL.findall(value):
        if not _LOCAL_URL.fullmatch(target.strip("'\" ")):
            raise UnsafeSvg(f"external url({target})")
    return value


def _clean_style(style: str) -> str:
    kept = []
    for declaration in style.split(";"):
        name, _sep, value = declaration.partition(":")
        name, value = name.strip(), value.strip()
        if name in STYLE_PROPERTIES and value:
            kept.append(f"{name}:{_check_urls(value)}")
    return ";".join(kept)


def _clean(element: ET.Element) -> None:
    if not element.tag.startswith(f"{{{SVG}}}") or _local(element.tag) not in ELEMENTS:
        raise UnsafeSvg(f"element <{_local(element.tag)}>")
    for name in list(element.attrib):
        value = element.attrib.pop(name)
        local = _local(name)
        if local == "style":
            value = _clean_style(value)
            local = "style" if value else ""
        elif local not in ATTRIBUTES:
            continue
        if local == "href":
            if not _LOCAL_URL.fullmatch(value):
                raise UnsafeSvg(f"href {value}")
            name = f"{{{XLINK}}}href"
        elif local:
            name = local
        else:
            continue
        element.set(name, _check_urls(value))
    element.text = (element.text or "").strip() or None
    element.tail = None
    for child in element:
        _clean(child)


def sanitize(source: str) -> str:
    """An allowlist pass: anything outside it is dropped (attributes) or refused (elements,
    DOCTYPE/entities, external references), so the result can't run script or load anything."""
    if re.search(r"<!(DOCTYPE|ENTITY)|<\?(?!xml\s)", source, re.IGNORECASE):
        raise UnsafeSvg("DOCTYPE, entity or processing instruction")
    # Safe without defusedxml: its attacks all need a DTD, refused just above.
    root = ET.fromstring(source)  # noqa: S314
    if root.tag != f"{{{SVG}}}svg":
        raise UnsafeSvg("root is not <svg>")
    _clean(root)
    root.attrib.pop("id", None)
    return ET.tostring(root, encoding="unicode")


def flag_url(code: str) -> str:
    return static(f"public/flags/{code.lower()}.svg")
