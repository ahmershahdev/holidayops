import time

import pytest
from django.core.cache import cache
from django.test import Client

from apps.public.status import HEARTBEAT_KEY, checks, releases
from apps.public.tasks import heartbeat

pytestmark = pytest.mark.django_db


def test_checks_report_each_part() -> None:
    cache.delete(HEARTBEAT_KEY)
    results = {c.name: c for c in checks()}
    assert results["Database"].ok
    assert results["Cache and rate limits"].ok
    assert not results["Feeds, digests and webhooks"].ok
    heartbeat()
    assert all(c.ok for c in checks())


def test_status_page_is_never_cached() -> None:
    cache.set(HEARTBEAT_KEY, time.time() - 3600)
    first = Client().get("/status/").content.decode()
    assert "Some parts need attention." in first
    heartbeat()
    assert "Everything is running." in Client().get("/status/").content.decode()


def test_changelog_renders_every_release() -> None:
    found = releases()
    assert found
    assert all(r.items for r in found)
    assert [r.day for r in found] == sorted((r.day for r in found), reverse=True)
    html = Client().get("/changelog/").content.decode()
    assert found[0].title in html
    assert Client().get("/ur/changelog/").status_code == 404
