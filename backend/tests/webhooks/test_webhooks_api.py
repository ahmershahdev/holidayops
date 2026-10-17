import json
from collections.abc import Callable
from typing import Any
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.orgs.models import AuditLog, Role
from apps.webhooks.models import EVENTS, Webhook, WebhookDelivery
from apps.webhooks.views import MAX_WEBHOOKS
from tests.factories import CalendarFactory, CustomDayFactory, MembershipFactory, SourceFactory
from tests.webhooks.conftest import FakeReceiver, addrinfo

pytestmark = pytest.mark.django_db

BODY = {"url": "https://hooks.example.com/in", "events": ["custom_day.created"]}


@pytest.fixture
def admin(client_for: Callable[[User], APIClient]) -> dict[str, Any]:
    membership = MembershipFactory.create(role=Role.ADMIN)
    url = f"/api/v1/orgs/{membership.org.slug}/webhooks/"
    return {"membership": membership, "url": url, "api": client_for(membership.user)}


def create(admin: dict[str, Any], **body: Any) -> dict[str, Any]:
    response = admin["api"].post(admin["url"], {**BODY, **body}, format="json")
    assert response.status_code == 201, response.data
    data: dict[str, Any] = response.data
    return data


def test_secret_is_shown_on_create_only(admin: dict[str, Any]) -> None:
    created = create(admin)
    assert created["secret"].startswith("whsec_")
    assert created["is_active"] is True
    assert created["created_by"] == admin["membership"].user.email
    detail = admin["api"].get(f"{admin['url']}{created['id']}/").data
    assert "secret" not in detail
    assert "secret" not in admin["api"].get(admin["url"]).data["results"][0]
    assert AuditLog.objects.filter(action="webhook.create").count() == 1


def test_events_are_validated_and_deduplicated(admin: dict[str, Any]) -> None:
    created = create(admin, events=["custom_day.deleted", "calendar.updated", "calendar.updated"])
    assert created["events"] == ["calendar.updated", "custom_day.deleted"]
    for events in ([], ["holiday.created"]):
        response = admin["api"].post(admin["url"], {**BODY, "events": events}, format="json")
        assert response.status_code == 400
    assert create(admin, events=EVENTS)["events"] == sorted(EVENTS)


@pytest.mark.parametrize(
    ("url", "address"),
    [
        ("http://hooks.example.com/", "93.184.216.34"),
        ("https://hooks.example.com/", "127.0.0.1"),
        ("https://metadata.example.com/", "169.254.169.254"),
    ],
)
def test_unsafe_urls_are_rejected(
    admin: dict[str, Any], dns: mock.MagicMock, url: str, address: str
) -> None:
    dns.return_value = addrinfo(address)
    response = admin["api"].post(admin["url"], {**BODY, "url": url}, format="json")
    assert response.status_code == 400
    assert "url" in response.data


def test_webhook_limit(admin: dict[str, Any]) -> None:
    for _ in range(MAX_WEBHOOKS):
        create(admin)
    assert admin["api"].post(admin["url"], BODY, format="json").status_code == 400


def test_members_cannot_see_or_manage_webhooks(
    admin: dict[str, Any], client_for: Callable[[User], APIClient]
) -> None:
    created = create(admin)
    member = MembershipFactory.create(org=admin["membership"].org, role=Role.MEMBER)
    api = client_for(member.user)
    assert api.get(admin["url"]).status_code == 403
    assert api.post(admin["url"], BODY, format="json").status_code == 403
    assert api.post(f"{admin['url']}{created['id']}/ping/").status_code == 403


def test_rotate_secret(admin: dict[str, Any]) -> None:
    created = create(admin)
    rotated = admin["api"].post(f"{admin['url']}{created['id']}/rotate-secret/").data
    assert rotated["secret"].startswith("whsec_")
    assert rotated["secret"] != created["secret"]
    assert Webhook.objects.get().secret == rotated["secret"]
    assert AuditLog.objects.filter(action="webhook.rotate").count() == 1


def test_reenabling_clears_the_failure_count(admin: dict[str, Any]) -> None:
    created = create(admin)
    Webhook.objects.update(is_active=False, failure_count=20)
    response = admin["api"].patch(
        f"{admin['url']}{created['id']}/", {"is_active": True}, format="json"
    )
    assert response.data["is_active"] is True
    assert response.data["failure_count"] == 0
    admin["api"].patch(f"{admin['url']}{created['id']}/", {"is_active": False}, format="json")
    Webhook.objects.update(failure_count=3)
    admin["api"].patch(f"{admin['url']}{created['id']}/", {"events": EVENTS}, format="json")
    assert Webhook.objects.get().failure_count == 3


def test_ping_and_delivery_log(
    admin: dict[str, Any], receiver: FakeReceiver, django_capture_on_commit_callbacks: Any
) -> None:
    created = create(admin)
    with django_capture_on_commit_callbacks(execute=True):
        response = admin["api"].post(f"{admin['url']}{created['id']}/ping/")
    assert response.status_code == 202
    assert response.data["event"] == "ping"
    assert receiver.calls[0]["headers"]["X-HolidayOps-Event"] == "ping"
    log = admin["api"].get(f"{admin['url']}{created['id']}/deliveries/").data
    assert [(d["event"], d["status"], d["response_status"]) for d in log] == [
        ("ping", "success", 200)
    ]


def test_delete(admin: dict[str, Any]) -> None:
    created = create(admin)
    assert admin["api"].delete(f"{admin['url']}{created['id']}/").status_code == 204
    assert not Webhook.objects.exists()
    assert AuditLog.objects.filter(action="webhook.delete").count() == 1


def test_calendar_changes_emit_events(
    admin: dict[str, Any], receiver: FakeReceiver, django_capture_on_commit_callbacks: Any
) -> None:
    create(admin, events=EVENTS)
    org = admin["membership"].org
    calendar = CalendarFactory.create(org=org, name="Karachi")
    SourceFactory.create(calendar=calendar)
    base = f"/api/v1/orgs/{org.slug}/calendars/{calendar.id}"
    api = admin["api"]
    with django_capture_on_commit_callbacks(execute=True):
        day = api.post(
            f"{base}/custom-days/",
            {"date": "2027-04-05", "name": "Office move", "kind": "closure"},
            format="json",
        ).data
    with django_capture_on_commit_callbacks(execute=True):
        api.patch(f"{base}/custom-days/{day['id']}/", {"name": "Move"}, format="json")
    with django_capture_on_commit_callbacks(execute=True):
        api.delete(f"{base}/custom-days/{day['id']}/")
    with django_capture_on_commit_callbacks(execute=True):
        api.patch(f"{base}/", {"name": "Lahore"}, format="json")
    with django_capture_on_commit_callbacks(execute=True):
        api.delete(f"{base}/")

    payloads = [json.loads(call["body"]) for call in receiver.calls]
    assert [p["event"] for p in payloads] == [
        "custom_day.created",
        "custom_day.updated",
        "custom_day.deleted",
        "calendar.updated",
        "calendar.deleted",
    ]
    assert payloads[0]["data"]["custom_day"] == {
        "id": day["id"],
        "date": "2027-04-05",
        "name": "Office move",
        "kind": "closure",
    }
    assert payloads[2]["data"]["custom_day"]["name"] == "Move"
    assert payloads[3]["data"]["calendar"]["name"] == "Lahore"
    assert payloads[4]["data"]["calendar"]["id"] == str(calendar.id)
    assert WebhookDelivery.objects.filter(status="success").count() == 5


def test_other_orgs_changes_do_not_reach_my_webhook(
    admin: dict[str, Any], receiver: FakeReceiver, django_capture_on_commit_callbacks: Any
) -> None:
    create(admin, events=EVENTS)
    stranger = MembershipFactory.create(role=Role.OWNER)
    CustomDayFactory.create(calendar=CalendarFactory.create(org=stranger.org))
    calendar = CalendarFactory.create(org=stranger.org)
    SourceFactory.create(calendar=calendar)
    api = APIClient()
    api.force_authenticate(stranger.user)
    with django_capture_on_commit_callbacks(execute=True):
        api.patch(
            f"/api/v1/orgs/{stranger.org.slug}/calendars/{calendar.id}/",
            {"name": "x"},
            format="json",
        )
    assert receiver.calls == []
