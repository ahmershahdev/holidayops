"""Limits that count then create must hold when requests arrive together."""

import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.api.models import ApiKey
from apps.feeds.models import FeedToken
from apps.feeds.views import MAX_ACTIVE_FEEDS
from apps.orgs import limits
from apps.orgs.invite_views import MAX_PENDING_INVITES
from apps.orgs.models import Invite, Membership, Role
from apps.webhooks.models import Webhook
from apps.webhooks.views import MAX_WEBHOOKS
from tests.factories import CalendarFactory, MembershipFactory

pytestmark = pytest.mark.django_db(transaction=True)


@dataclass
class Case:
    path: str
    limit: int
    body: Callable[[int], dict[str, Any]]
    count: Callable[[Membership], int]


CASES = {
    "api_keys": Case(
        "api-keys/",
        3,
        lambda n: {"name": f"key {n}"},
        lambda m: ApiKey.objects.filter(org=m.org).count(),
    ),
    "invites": Case(
        "invites/",
        MAX_PENDING_INVITES,
        lambda n: {"email": f"person{n}@example.com", "role": Role.MEMBER},
        lambda m: Invite.objects.filter(org=m.org).count(),
    ),
    "webhooks": Case(
        "webhooks/",
        MAX_WEBHOOKS,
        lambda n: {"url": f"https://hooks.example.com/{n}", "events": ["calendar.updated"]},
        lambda m: Webhook.objects.filter(org=m.org).count(),
    ),
    "feeds": Case(
        "calendars/{calendar}/feeds/",
        MAX_ACTIVE_FEEDS,
        lambda n: {"label": f"feed {n}"},
        lambda m: FeedToken.objects.filter(calendar__org=m.org).count(),
    ),
}


@pytest.fixture(autouse=True)
def _public_dns() -> Iterator[None]:
    with mock.patch("apps.webhooks.net.resolve", return_value=["93.184.216.34"]):
        yield


@pytest.fixture
def owner() -> Membership:
    return MembershipFactory.create(role=Role.OWNER)


def url_for(owner: Membership, case: Case) -> str:
    calendar = CalendarFactory.create(org=owner.org) if "{calendar}" in case.path else None
    path = case.path.format(calendar=calendar.id if calendar else "")
    return f"/api/v1/orgs/{owner.org.slug}/{path}"


def post(owner: Membership, url: str, body: dict[str, Any]) -> int:
    api = APIClient()
    api.force_authenticate(owner.user)
    status: int = api.post(url, body, format="json").status_code
    return status


def slow_count(queryset: Any) -> int:
    counted: int = queryset.count()
    time.sleep(0.3)
    return counted


def fill(owner: Membership, url: str, case: Case, n: int) -> None:
    if case.path == "invites/":
        # Invites have a per-user request throttle well below the limit; insert them directly.
        Invite.objects.bulk_create(
            Invite(
                org=owner.org,
                email=f"p{i}@example.com",
                role=Role.VIEWER,
                token_hash=f"{i:064d}",
                expires_at=timezone.now() + timedelta(days=1),
            )
            for i in range(n)
        )
        return
    for i in range(n):
        assert post(owner, url, case.body(i)) == 201


@pytest.mark.parametrize("name", CASES)
def test_concurrent_creates_stop_at_the_limit(owner: Membership, name: str) -> None:
    case = CASES[name]
    url = url_for(owner, case)
    fill(owner, url, case, case.limit - 1)

    results: list[int] = []
    start = threading.Barrier(2)

    def worker(n: int) -> None:
        try:
            start.wait()
            results.append(post(owner, url, case.body(n)))
        finally:
            connection.close()

    with mock.patch.object(limits, "_count", side_effect=slow_count):
        threads = [threading.Thread(target=worker, args=(100 + i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert sorted(results) == [201, 400]
    assert case.count(owner) == case.limit


def test_a_held_lock_answers_busy_instead_of_waiting_forever(owner: Membership) -> None:
    url = url_for(owner, CASES["api_keys"])
    held, release = threading.Event(), threading.Event()

    def holder() -> None:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT GET_LOCK(%s, 5)", [f"hops:api_keys:{owner.org.pk}"])
                held.set()
                release.wait(5)
                cursor.execute("SELECT RELEASE_LOCK(%s)", [f"hops:api_keys:{owner.org.pk}"])
        finally:
            connection.close()

    thread = threading.Thread(target=holder)
    thread.start()
    held.wait(5)
    try:
        with mock.patch.object(limits, "LOCK_TIMEOUT", 0):
            assert post(owner, url, {"name": "blocked"}) == 409
    finally:
        release.set()
        thread.join()
    assert post(owner, url, {"name": "after"}) == 201
