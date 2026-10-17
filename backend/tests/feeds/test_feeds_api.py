import datetime
from collections.abc import Callable
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.calendars.models import CustomDay
from apps.feeds.models import FeedToken
from apps.feeds.views import MAX_ACTIVE_FEEDS
from apps.orgs.models import AuditLog, Role
from tests.factories import CalendarFactory, MembershipFactory, SourceFactory

pytestmark = pytest.mark.django_db

THIS_YEAR = timezone.now().year


@pytest.fixture
def setup(client_for: Callable[[User], APIClient]) -> dict[str, Any]:
    member = MembershipFactory.create(role=Role.MEMBER)
    calendar = CalendarFactory.create(org=member.org, name="Karachi office", slug="karachi")
    SourceFactory.create(calendar=calendar, country="PK")
    url = f"/api/v1/orgs/{member.org.slug}/calendars/{calendar.id}/feeds/"
    return {"member": member, "calendar": calendar, "url": url, "api": client_for(member.user)}


def create_feed(setup: dict[str, Any], label: str = "Outlook") -> dict[str, Any]:
    response = setup["api"].post(setup["url"], {"label": label}, format="json")
    assert response.status_code == 201, response.data
    data: dict[str, Any] = response.data
    return data


def feed_path(created: dict[str, Any]) -> str:
    url: str = created["url"]
    return "/feeds/" + url.split("/feeds/", 1)[1]


def test_create_returns_url_once_and_stores_only_a_hash(setup: dict[str, Any]) -> None:
    created = create_feed(setup)
    token = feed_path(created).removeprefix("/feeds/").removesuffix(".ics")
    assert created["url"].startswith("http://testserver/feeds/")
    assert created["label"] == "Outlook"
    assert created["created_by"] == setup["member"].user.email
    assert len(token) >= 43
    assert not FeedToken.objects.filter(token_hash=token).exists()

    listed = setup["api"].get(setup["url"]).data["results"]
    assert [f["label"] for f in listed] == ["Outlook"]
    assert "url" not in listed[0]
    assert AuditLog.objects.filter(action="feed.create").count() == 1


def test_feed_is_public_ical(setup: dict[str, Any]) -> None:
    CustomDay.objects.create(
        calendar=setup["calendar"],
        date=datetime.date(THIS_YEAR, 6, 15),
        name="Office move",
        kind="closure",
    )
    response = APIClient().get(feed_path(create_feed(setup)), HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/calendar; charset=utf-8"
    assert response["Cache-Control"] == "private, max-age=3600"
    assert 'filename="karachi.ics"' in response["Content-Disposition"]
    body = response.content.decode()
    assert "X-WR-CALNAME:Karachi office" in body
    assert f"DTSTART;VALUE=DATE:{THIS_YEAR}0323" in body
    assert f"DTSTART;VALUE=DATE:{THIS_YEAR - 1}0323" in body
    assert f"DTSTART;VALUE=DATE:{THIS_YEAR + 1}0323" in body
    assert f"DTSTART;VALUE=DATE:{THIS_YEAR + 2}0323" not in body
    assert "SUMMARY:Office move\r\nCATEGORIES:CLOSURE" in body
    assert FeedToken.objects.get().last_used_at is not None


def test_etag_allows_conditional_requests(setup: dict[str, Any]) -> None:
    path = feed_path(create_feed(setup))
    etag = APIClient().get(path)["ETag"]
    response = APIClient().get(path, HTTP_IF_NONE_MATCH=etag)
    assert response.status_code == 304
    assert response.content == b""


def test_custom_day_change_refreshes_the_cached_feed(setup: dict[str, Any]) -> None:
    path = feed_path(create_feed(setup))
    assert "Stock count" not in APIClient().get(path).content.decode()
    day = setup["api"].post(
        f"/api/v1/orgs/{setup['member'].org.slug}/calendars/{setup['calendar'].id}/custom-days/",
        {"date": f"{THIS_YEAR}-07-03", "name": "Stock count", "kind": "working_day"},
        format="json",
    )
    assert day.status_code == 201
    assert "Stock count" in APIClient().get(path).content.decode()
    CustomDay.objects.get(name="Stock count").delete()
    assert "Stock count" not in APIClient().get(path).content.decode()


def test_calendar_rename_refreshes_the_cached_feed(setup: dict[str, Any]) -> None:
    path = feed_path(create_feed(setup))
    APIClient().get(path)
    setup["api"].patch(
        f"/api/v1/orgs/{setup['member'].org.slug}/calendars/{setup['calendar'].id}/",
        {"name": "Lahore office"},
        format="json",
    )
    assert "X-WR-CALNAME:Lahore office" in APIClient().get(path).content.decode()


def test_unknown_and_revoked_tokens_are_404(setup: dict[str, Any]) -> None:
    assert APIClient().get("/feeds/not-a-real-token.ics").status_code == 404
    created = create_feed(setup)
    assert setup["api"].delete(f"{setup['url']}{created['id']}/").status_code == 204
    assert APIClient().get(feed_path(created)).status_code == 404
    assert setup["api"].get(setup["url"]).data["count"] == 0
    assert AuditLog.objects.filter(action="feed.revoke").count() == 1


def test_rotate_revokes_the_old_url_and_keeps_the_label(setup: dict[str, Any]) -> None:
    old = create_feed(setup, "Google")
    response = setup["api"].post(f"{setup['url']}{old['id']}/rotate/")
    assert response.status_code == 201
    new = response.data
    assert new["label"] == "Google"
    assert new["url"] != old["url"]
    assert APIClient().get(feed_path(old)).status_code == 404
    assert APIClient().get(feed_path(new)).status_code == 200
    assert AuditLog.objects.filter(action="feed.rotate").count() == 1


def test_active_feed_limit(setup: dict[str, Any]) -> None:
    for n in range(MAX_ACTIVE_FEEDS):
        create_feed(setup, f"Feed {n}")
    response = setup["api"].post(setup["url"], {"label": "One too many"}, format="json")
    assert response.status_code == 400


def test_viewer_can_list_but_not_manage(
    setup: dict[str, Any], client_for: Callable[[User], APIClient]
) -> None:
    created = create_feed(setup)
    viewer = MembershipFactory.create(org=setup["member"].org, role=Role.VIEWER)
    api = client_for(viewer.user)
    assert api.get(setup["url"]).status_code == 200
    assert api.post(setup["url"], {"label": "x"}, format="json").status_code == 403
    assert api.post(f"{setup['url']}{created['id']}/rotate/").status_code == 403
    assert api.delete(f"{setup['url']}{created['id']}/").status_code == 403


def test_feed_of_another_calendar_is_404(setup: dict[str, Any]) -> None:
    created = create_feed(setup)
    other = CalendarFactory.create(org=setup["member"].org)
    url = f"/api/v1/orgs/{setup['member'].org.slug}/calendars/{other.id}/feeds/{created['id']}/"
    assert setup["api"].delete(url).status_code == 404


def test_deleted_calendar_takes_its_feeds_with_it(setup: dict[str, Any]) -> None:
    path = feed_path(create_feed(setup))
    setup["calendar"].delete()
    assert APIClient().get(path).status_code == 404
