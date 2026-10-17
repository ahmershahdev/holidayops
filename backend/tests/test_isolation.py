"""A user from another org must get 404 on every org-scoped endpoint, so existence never leaks."""

from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.calendars.models import Calendar, CustomDay
from apps.feeds.models import FeedToken
from apps.orgs.models import Membership, Role
from tests.factories import CalendarFactory, CustomDayFactory, MembershipFactory, SourceFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def victim() -> dict[str, Any]:
    owner = MembershipFactory.create(role=Role.OWNER)
    other = MembershipFactory.create(org=owner.org, role=Role.VIEWER)
    calendar = CalendarFactory.create(org=owner.org)
    SourceFactory.create(calendar=calendar)
    day = CustomDayFactory.create(calendar=calendar)
    feed = FeedToken(org=owner.org, calendar=calendar, label="Outlook")
    feed.set_new_token()
    feed.save()
    return {"org": owner.org, "member": other, "calendar": calendar, "day": day, "feed": feed}


def endpoints(v: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    org = f"/api/v1/orgs/{v['org'].slug}"
    cal = f"{org}/calendars/{v['calendar'].id}"
    day = f"{cal}/custom-days/{v['day'].id}/"
    feed = f"{cal}/feeds/{v['feed'].id}/"
    return [
        ("get", f"{org}/", {}),
        ("patch", f"{org}/", {"name": "pwned"}),
        ("delete", f"{org}/", {}),
        ("get", f"{org}/members/", {}),
        ("post", f"{org}/members/", {"email": "x@example.com", "role": "viewer"}),
        ("patch", f"{org}/members/{v['member'].id}/", {"role": "admin"}),
        ("delete", f"{org}/members/{v['member'].id}/", {}),
        ("get", f"{org}/audit-log/", {}),
        ("get", f"{org}/calendars/", {}),
        ("post", f"{org}/calendars/", {"name": "x", "sources": [{"country": "PK"}]}),
        ("get", f"{cal}/", {}),
        ("patch", f"{cal}/", {"name": "pwned"}),
        ("delete", f"{cal}/", {}),
        ("get", f"{cal}/custom-days/", {}),
        ("post", f"{cal}/custom-days/", {"date": "2027-01-01", "name": "x", "kind": "closure"}),
        ("get", day, {}),
        ("patch", day, {"name": "pwned"}),
        ("delete", day, {}),
        ("get", f"{cal}/feeds/", {}),
        ("post", f"{cal}/feeds/", {"label": "x"}),
        ("delete", feed, {}),
        ("post", f"{feed}rotate/", {}),
        ("get", f"{cal}/digest/", {}),
        ("put", f"{cal}/digest/", {}),
        ("delete", f"{cal}/digest/", {}),
        (
            "get",
            "/api/v1/business-days/check/",
            {"calendar": v["calendar"].id, "date": "2027-01-04"},
        ),
        ("get", "/api/v1/holidays/", {"calendar": v["calendar"].id, "year": 2027}),
    ]


def test_every_org_endpoint_returns_404_to_outsiders(
    victim: dict[str, Any], client_for: Callable[[User], APIClient]
) -> None:
    outsider = MembershipFactory.create(role=Role.OWNER).user
    client = client_for(outsider)
    for method, url, data in endpoints(victim):
        kwargs = {"format": "json"} if method in {"post", "patch", "put"} else {}
        response = getattr(client, method)(url, data, **kwargs)
        assert response.status_code == 404, f"{method.upper()} {url} -> {response.status_code}"

    assert Membership.objects.filter(org=victim["org"]).count() == 2
    assert Calendar.objects.filter(pk=victim["calendar"].pk, name=victim["calendar"].name).exists()
    assert CustomDay.objects.filter(pk=victim["day"].pk, name="Office move").exists()
    assert (
        FeedToken.objects.filter(calendar=victim["calendar"], revoked_at__isnull=True).count() == 1
    )


def test_nested_custom_day_of_another_org_is_404(
    client_for: Callable[[User], APIClient],
) -> None:
    mine = MembershipFactory.create(role=Role.OWNER)
    my_calendar = CalendarFactory.create(org=mine.org)
    their_day = CustomDayFactory.create()
    url = f"/api/v1/orgs/{mine.org.slug}/calendars/{my_calendar.id}/custom-days/{their_day.id}/"
    assert client_for(mine.user).get(url).status_code == 404
    other_cal = f"/api/v1/orgs/{mine.org.slug}/calendars/{their_day.calendar.id}/custom-days/"
    assert client_for(mine.user).get(other_cal).status_code == 404
