"""Live checks for /status/ and the changelog parser for /changelog/."""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from functools import cache as memoize
from importlib.metadata import version
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils.translation import gettext as _

from apps.core import list_countries

HEARTBEAT_KEY = "worker:heartbeat"
# Beat sends a heartbeat every minute; three missed ones mean the worker or Beat is down.
HEARTBEAT_STALE = 180


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    ms: int | None = None


def _timed(probe: Callable[[], bool]) -> tuple[bool, int]:
    start = time.perf_counter()
    try:
        ok = probe()
    except Exception:
        ok = False
    return ok, round((time.perf_counter() - start) * 1000)


def _database() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        return bool(cursor.fetchone() == (1,))


def _cache() -> bool:
    cache.set("status:probe", "1", timeout=10)
    return bool(cache.get("status:probe") == "1")


def checks() -> list[Check]:
    db_ok, db_ms = _timed(_database)
    cache_ok, cache_ms = _timed(_cache)
    beat = cache.get(HEARTBEAT_KEY)
    age = time.time() - beat if beat else None
    jobs_ok = age is not None and age < HEARTBEAT_STALE
    return [
        Check(_("API and website"), True, _("Answering requests")),
        Check(_("Database"), db_ok, _("Connected") if db_ok else _("Not answering"), db_ms),
        Check(
            _("Cache and rate limits"),
            cache_ok,
            _("Connected") if cache_ok else _("Not answering"),
            cache_ms,
        ),
        Check(
            _("Feeds, digests and webhooks"),
            jobs_ok,
            _("Last heartbeat %(seconds)s s ago") % {"seconds": int(age)}
            if age is not None
            else _("No heartbeat yet"),
        ),
        Check(
            _("Holiday data"),
            True,
            _("holidays %(version)s, %(count)s countries")
            % {"version": version("holidays"), "count": len(list_countries())},
        ),
    ]


@dataclass(frozen=True)
class Release:
    day: date
    title: str
    items: tuple[str, ...]


_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2}): (.+)$")


def changelog_path() -> Path:
    # The repository root in development, next to manage.py in the image.
    for path in (settings.BASE_DIR / "CHANGELOG.md", settings.BASE_DIR.parent / "CHANGELOG.md"):
        if path.is_file():
            return path
    raise FileNotFoundError("CHANGELOG.md")


@memoize
def releases() -> tuple[Release, ...]:
    """CHANGELOG.md in its restricted format: `## YYYY-MM-DD: Title` then `- item` lines."""
    found: list[Release] = []
    for line in changelog_path().read_text(encoding="utf-8").splitlines():
        heading = _HEADING.match(line)
        if heading:
            found.append(Release(date.fromisoformat(heading[1]), heading[2], ()))
        elif line.startswith("- ") and found:
            last = found[-1]
            found[-1] = Release(last.day, last.title, (*last.items, line[2:].strip()))
    return tuple(found)
