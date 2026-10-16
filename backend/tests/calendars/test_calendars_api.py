from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.orgs.models import AuditLog, Role
from tests.factories import CalendarFactory, CustomDayFactory, MembershipFactory, SourceFactory

pytestmark = pytest.mark.django_db

ClientFor = Callable[[User], APIClient]

PAYLOAD: dict[str, Any] = {
    "name": "Karachi + Riyadh offices",
    "language": "en_US",
    "sources": [{"country": "pk"}, {"country": "SA", "categories": ["public"]}],
}


def test_create_and_update_calendar(client_for: ClientFor) -> None:
    owner = MembershipFactory.create(role=Role.MEMBER)
    client = client_for(owner.user)
    base = f"/api/v1/orgs/{owner.org.slug}/calendars/"

    created = client.post(base, PAYLOAD, format="json")
    assert created.status_code == 201
    body = created.json()
    assert body["slug"] == "karachi-riyadh-offices"
    assert body["weekend"] is None
    assert [s["country"] for s in body["sources"]] == ["PK", "SA"]

    url = f"{base}{body['id']}/"
    updated = client.patch(url, {"weekend": [4, 5], "sources": [{"country": "AE"}]}, format="json")
    assert updated.status_code == 200
    assert updated.json()["weekend"] == [4, 5]
    assert [s["country"] for s in updated.json()["sources"]] == ["AE"]
    assert client.get(base).json()["count"] == 1


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"sources": []}, "sources"),
        ({"sources": [{"country": "ZZ"}]}, "sources"),
        ({"sources": [{"country": "US", "subdiv": "XX"}]}, "sources"),
        ({"sources": [{"country": "PK", "categories": ["nope"]}]}, "sources"),
        ({"weekend": [5, 5]}, "weekend"),
        ({"weekend": [7]}, "weekend"),
        ({"language": "de"}, "language"),
    ],
)
def test_calendar_validation(client_for: ClientFor, change: dict[str, Any], field: str) -> None:
    owner = MembershipFactory.create()
    response = client_for(owner.user).post(
        f"/api/v1/orgs/{owner.org.slug}/calendars/", {**PAYLOAD, **change}, format="json"
    )
    assert response.status_code == 400
    assert field in response.json()


def test_viewer_cannot_write_and_member_cannot_delete(client_for: ClientFor) -> None:
    viewer = MembershipFactory.create(role=Role.VIEWER)
    member = MembershipFactory.create(org=viewer.org, role=Role.MEMBER)
    admin = MembershipFactory.create(org=viewer.org, role=Role.ADMIN)
    calendar = CalendarFactory.create(org=viewer.org)
    base = f"/api/v1/orgs/{viewer.org.slug}/calendars/"

    assert client_for(viewer.user).get(base).status_code == 200
    assert client_for(viewer.user).post(base, PAYLOAD, format="json").status_code == 403
    assert client_for(member.user).delete(f"{base}{calendar.id}/").status_code == 403
    assert client_for(admin.user).delete(f"{base}{calendar.id}/").status_code == 204
    assert AuditLog.objects.filter(org=viewer.org, action="calendar.delete").exists()


def test_custom_days_crud_and_year_filter(client_for: ClientFor) -> None:
    owner = MembershipFactory.create()
    calendar = CalendarFactory.create(org=owner.org)
    client = client_for(owner.user)
    base = f"/api/v1/orgs/{owner.org.slug}/calendars/{calendar.id}/custom-days/"

    day = {"date": "2027-04-05", "name": "Office move", "kind": "closure"}
    created = client.post(base, day)
    assert created.status_code == 201
    assert client.post(base, day).status_code == 400
    client.post(base, {"date": "2028-01-03", "name": "Retreat", "kind": "closure"})
    assert client.get(base, {"year": 2027}).json()["count"] == 1
    url = f"{base}{created.json()['id']}/"
    assert client.patch(url, {"kind": "half_day"}).json()["kind"] == "half_day"
    assert client.delete(url).status_code == 204
    assert (
        client.post(base, {"date": "1900-01-01", "name": "x", "kind": "closure"}).status_code == 400
    )


def test_business_days_with_company_calendar(client_for: ClientFor, client: APIClient) -> None:
    owner = MembershipFactory.create()
    calendar = CalendarFactory.create(org=owner.org, language="en_US")
    SourceFactory.create(calendar=calendar, country="PK")
    CustomDayFactory.create(
        calendar=calendar, date="2027-04-05", name="Office move", kind="closure"
    )
    CustomDayFactory.create(calendar=calendar, date="2027-03-23", name="Payroll", kind="half_day")
    member = client_for(owner.user)
    cal = str(calendar.id)

    check = member.get("/api/v1/business-days/check/", {"calendar": cal, "date": "2027-04-05"})
    assert check.json()["reason"] == "closure"
    half = member.get("/api/v1/business-days/check/", {"calendar": cal, "date": "2027-03-23"})
    assert half.json()["half_day"] is True
    added = member.get(
        "/api/v1/business-days/add/", {"calendar": cal, "date": "2027-04-02", "days": "1"}
    )
    assert added.json()["result"] == "2027-04-06"
    between = member.get(
        "/api/v1/business-days/between/",
        {"calendar": cal, "start": "2027-04-01", "end": "2027-04-07"},
    )
    assert between.json()["business_days"] == 4

    listed = member.get("/api/v1/holidays/", {"calendar": cal, "year": "2027"}).json()
    assert listed["country"] is None
    assert listed["calendar"] == cal
    kinds = {(h["date"], h["kind"]) for h in listed["holidays"]}
    assert ("2027-04-05", "closure") in kinds
    assert ("2027-03-23", "half_day") in kinds
    assert ("2027-03-23", "holiday") not in kinds
    sources = {(h["date"], h["kind"]): h["sources"] for h in listed["holidays"]}
    assert sources[("2027-03-23", "half_day")] == []
    assert sources[("2027-04-05", "closure")] == []
    assert sources[("2027-02-05", "holiday")] == ["PK"]

    week = member.get(
        "/api/v1/business-days/range/",
        {"calendar": cal, "start": "2027-04-04", "end": "2027-04-06"},
    ).json()
    assert [d["reason"] for d in week] == ["weekend", "closure", "working_day"]

    assert (
        client.get(
            "/api/v1/business-days/check/", {"calendar": cal, "date": "2027-04-05"}
        ).status_code
        == 404
    )
    calendar.is_public = True
    calendar.save()
    assert (
        client.get(
            "/api/v1/business-days/check/", {"calendar": cal, "date": "2027-04-05"}
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "params",
    [
        {"date": "2027-04-05"},
        {"date": "2027-04-05", "country": "PK", "calendar": "00000000-0000-0000-0000-000000000000"},
        {"date": "2027-04-05", "calendar": "00000000-0000-0000-0000-000000000000", "subdiv": "x"},
    ],
)
def test_country_or_calendar_is_required(client: APIClient, params: dict[str, str]) -> None:
    assert client.get("/api/v1/business-days/check/", params).status_code == 400


def test_patch_language_is_checked_against_existing_sources(client_for: ClientFor) -> None:
    owner = MembershipFactory.create()
    calendar = CalendarFactory.create(org=owner.org)
    SourceFactory.create(calendar=calendar, country="PK")
    url = f"/api/v1/orgs/{owner.org.slug}/calendars/{calendar.id}/"
    client = client_for(owner.user)
    assert client.patch(url, {"language": "ar"}, format="json").status_code == 400
    assert client.patch(url, {"language": "ur_PK"}, format="json").json()["language"] == "ur_PK"
