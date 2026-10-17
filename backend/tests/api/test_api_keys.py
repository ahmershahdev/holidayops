import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.api.models import ApiKey, UsageEvent
from apps.api.tasks import prune_usage
from apps.api.throttles import AnonRateThrottle
from apps.api.usage import seconds_until_next_month
from apps.orgs.models import AuditLog, Organization, Role
from tests.factories import CalendarFactory, MembershipFactory, SourceFactory

pytestmark = pytest.mark.django_db

KEY_FORMAT = re.compile(r"^hops_[0-9a-f]{8}_[\w-]{43}$")


@pytest.fixture
def owner(client_for: Callable[[User], APIClient]) -> dict[str, Any]:
    membership = MembershipFactory.create(role=Role.OWNER)
    org = membership.org
    return {
        "membership": membership,
        "org": org,
        "url": f"/api/v1/orgs/{org.slug}/api-keys/",
        "usage": f"/api/v1/orgs/{org.slug}/usage/",
        "api": client_for(membership.user),
    }


def new_key(owner: dict[str, Any], name: str = "Payroll") -> str:
    response = owner["api"].post(owner["url"], {"name": name}, format="json")
    assert response.status_code == 201, response.data
    key: str = response.data["key"]
    return key


def keyed(key: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {key}")
    return client


def test_key_is_shown_once_and_stored_hashed(owner: dict[str, Any]) -> None:
    key = new_key(owner)
    assert KEY_FORMAT.match(key)
    stored = ApiKey.objects.get()
    assert key.split("_")[1] == stored.prefix
    assert key not in stored.key_hash
    listed = owner["api"].get(owner["url"]).data
    assert [(k["name"], k["prefix"]) for k in listed] == [("Payroll", stored.prefix)]
    assert "key" not in listed[0]
    assert AuditLog.objects.filter(action="api_key.create").count() == 1


def test_only_owners_manage_keys_and_admins_can_look(
    owner: dict[str, Any], client_for: Callable[[User], APIClient]
) -> None:
    new_key(owner)
    admin = client_for(MembershipFactory.create(org=owner["org"], role=Role.ADMIN).user)
    member = client_for(MembershipFactory.create(org=owner["org"], role=Role.MEMBER).user)
    assert admin.get(owner["url"]).status_code == 200
    assert admin.get(owner["usage"]).status_code == 200
    assert admin.post(owner["url"], {"name": "x"}, format="json").status_code == 403
    assert admin.delete(f"{owner['url']}{ApiKey.objects.get().pk}/").status_code == 403
    assert member.get(owner["url"]).status_code == 403
    assert member.get(owner["usage"]).status_code == 403


def test_plan_caps_active_keys(owner: dict[str, Any]) -> None:
    for n in range(3):
        new_key(owner, f"k{n}")
    assert owner["api"].post(owner["url"], {"name": "k4"}, format="json").status_code == 400
    call_command("set_plan", owner["org"].slug, "pro")
    new_key(owner, "k4")


def test_key_authenticates_public_endpoints(owner: dict[str, Any]) -> None:
    key = new_key(owner)
    response = keyed(key).get("/api/v1/business-days/check/?country=PK&date=2027-03-23")
    assert response.status_code == 200
    assert response.data["reason"] == "holiday"
    event = UsageEvent.objects.get()
    assert (event.endpoint, event.status, event.org_id) == (
        "business-days-check",
        200,
        owner["org"].pk,
    )
    assert ApiKey.objects.get().last_used_at is not None


def test_bad_keys_get_401_with_bearer_challenge(owner: dict[str, Any]) -> None:
    key = new_key(owner)
    prefix = key.split("_")[1]
    for bad in (f"hops_{prefix}_{'x' * 43}", "hops_nope", "hops_zzzzzzzz_secret"):
        response = keyed(bad).get("/api/v1/countries/")
        assert response.status_code == 401, bad
        assert response["WWW-Authenticate"] == "Bearer"
    assert not UsageEvent.objects.exists()


def test_other_authorization_headers_are_ignored() -> None:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer some-other-token")
    assert client.get("/api/v1/countries/").status_code == 200
    client.credentials(HTTP_AUTHORIZATION="Basic dXNlcjpwYXNz")
    assert client.get("/api/v1/countries/").status_code == 200


def test_revoked_key_stops_working(owner: dict[str, Any]) -> None:
    key = new_key(owner)
    pk = ApiKey.objects.get().pk
    assert owner["api"].delete(f"{owner['url']}{pk}/").status_code == 204
    assert keyed(key).get("/api/v1/countries/").status_code == 401
    assert owner["api"].get(owner["url"]).data == []
    assert AuditLog.objects.filter(action="api_key.revoke").count() == 1


def test_keys_do_not_open_org_management(owner: dict[str, Any]) -> None:
    key = new_key(owner)
    assert keyed(key).get(f"/api/v1/orgs/{owner['org'].slug}/").status_code == 403
    assert keyed(key).get(owner["url"]).status_code == 403


def test_key_reaches_its_orgs_private_calendars_only(owner: dict[str, Any]) -> None:
    key = new_key(owner)
    mine = CalendarFactory.create(org=owner["org"])
    SourceFactory.create(calendar=mine)
    theirs = CalendarFactory.create()
    SourceFactory.create(calendar=theirs)
    client = keyed(key)
    assert client.get(f"/api/v1/holidays/?calendar={mine.id}&year=2027").status_code == 200
    assert client.get(f"/api/v1/holidays/?calendar={theirs.id}&year=2027").status_code == 404


def test_per_key_rate_follows_the_plan(owner: dict[str, Any], settings: Any) -> None:
    settings.PLANS = {**settings.PLANS, "free": {**settings.PLANS["free"], "rate": "2/minute"}}
    first, second = new_key(owner, "a"), new_key(owner, "b")
    for _ in range(2):
        assert keyed(first).get("/api/v1/countries/").status_code == 200
    throttled = keyed(first).get("/api/v1/countries/")
    assert throttled.status_code == 429
    assert int(throttled["Retry-After"]) > 0
    assert keyed(second).get("/api/v1/countries/").status_code == 200


def test_monthly_quota_per_org(owner: dict[str, Any], settings: Any) -> None:
    settings.PLANS = {
        **settings.PLANS,
        "free": {**settings.PLANS["free"], "monthly_quota": 2},
    }
    key = new_key(owner)
    for _ in range(2):
        assert keyed(key).get("/api/v1/countries/").status_code == 200
    over = keyed(key).get("/api/v1/countries/")
    assert over.status_code == 429
    assert int(over["Retry-After"]) <= 31 * 24 * 3600
    keyed(key).get("/api/v1/countries/")
    usage = owner["api"].get(owner["usage"]).data
    assert usage["used_this_month"] == 2
    assert usage["monthly_quota"] == 2


def test_anonymous_ip_limit_does_not_apply_to_keyed_requests() -> None:
    throttle = AnonRateThrottle()
    keyed_request: Any = SimpleNamespace(auth=ApiKey(prefix="abcd1234"))
    assert throttle.get_cache_key(keyed_request, None) is None


def test_month_boundary_maths() -> None:
    assert seconds_until_next_month(datetime(2027, 12, 31, 23, 59, 30, tzinfo=UTC)) == 30
    assert seconds_until_next_month(datetime(2027, 2, 1, tzinfo=UTC)) == 28 * 24 * 3600


def test_usage_report(owner: dict[str, Any]) -> None:
    key = new_key(owner)
    client = keyed(key)
    client.get("/api/v1/countries/")
    client.get("/api/v1/business-days/check/?country=PK&date=not-a-date")
    old = UsageEvent.objects.create(
        org=owner["org"], api_key=ApiKey.objects.get(), endpoint="countries", status=200
    )
    UsageEvent.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=2))

    data = owner["api"].get(owner["usage"]).data
    assert data["plan"] == "free"
    assert data["rate"] == "120/minute"
    assert data["max_keys"] == 3
    assert data["used_this_month"] >= 2
    days = data["days"]
    assert len(days) == 30
    assert days[-1]["date"] == timezone.now().date().isoformat()
    assert (days[-1]["requests"], days[-1]["failed"]) == (2, 1)
    assert days[-3]["requests"] == 1
    assert sum(d["requests"] for d in days) == 3
    assert len(owner["api"].get(f"{owner['usage']}?days=7").data["days"]) == 7
    assert len(owner["api"].get(f"{owner['usage']}?days=999").data["days"]) == 90
    assert len(owner["api"].get(f"{owner['usage']}?days=0").data["days"]) == 1
    assert len(owner["api"].get(f"{owner['usage']}?days=abc").data["days"]) == 30


def test_session_and_anonymous_calls_are_not_recorded(owner: dict[str, Any]) -> None:
    owner["api"].get("/api/v1/countries/")
    APIClient().get("/api/v1/countries/")
    assert not UsageEvent.objects.exists()


def test_old_usage_is_pruned(owner: dict[str, Any]) -> None:
    new_key(owner)
    api_key = ApiKey.objects.get()
    keep = UsageEvent.objects.create(org=owner["org"], api_key=api_key, endpoint="x", status=200)
    drop = UsageEvent.objects.create(org=owner["org"], api_key=api_key, endpoint="x", status=200)
    UsageEvent.objects.filter(pk=drop.pk).update(created_at=timezone.now() - timedelta(days=91))
    assert prune_usage.delay().get() == 1
    assert list(UsageEvent.objects.values_list("pk", flat=True)) == [keep.pk]


def test_set_plan_command(owner: dict[str, Any]) -> None:
    call_command("set_plan", owner["org"].slug, "pro")
    assert Organization.objects.get(pk=owner["org"].pk).plan == "pro"
    with pytest.raises(CommandError):
        call_command("set_plan", "no-such-org", "pro")
