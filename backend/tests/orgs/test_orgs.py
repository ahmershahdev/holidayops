from collections.abc import Callable

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.orgs.models import AuditLog, Membership, Role
from tests.factories import MembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

ClientFor = Callable[[User], APIClient]


def test_create_org_makes_creator_owner(client_for: ClientFor) -> None:
    user = UserFactory.create()
    client = client_for(user)
    response = client.post("/api/v1/orgs/", {"name": "Acme Payroll"})
    assert response.status_code == 201
    assert response.json()["slug"] == "acme-payroll"
    assert response.json()["role"] == "owner"
    second = client.post("/api/v1/orgs/", {"name": "Acme Payroll"})
    assert second.json()["slug"] == "acme-payroll-2"
    assert [o["slug"] for o in client.get("/api/v1/orgs/").json()] == [
        "acme-payroll",
        "acme-payroll-2",
    ]


def test_anonymous_cannot_use_org_endpoints(client: APIClient) -> None:
    assert client.get("/api/v1/orgs/").status_code == 403


def test_org_update_needs_admin_and_delete_needs_owner(client_for: ClientFor) -> None:
    owner = MembershipFactory.create(role=Role.OWNER)
    org = owner.org
    admin = MembershipFactory.create(org=org, role=Role.ADMIN)
    member = MembershipFactory.create(org=org, role=Role.MEMBER)
    url = f"/api/v1/orgs/{org.slug}/"

    assert client_for(member.user).get(url).json()["role"] == "member"
    assert client_for(member.user).patch(url, {"name": "X"}).status_code == 403
    assert client_for(admin.user).patch(url, {"name": "Renamed"}).json()["name"] == "Renamed"
    assert client_for(admin.user).delete(url).status_code == 403
    assert client_for(owner.user).delete(url).status_code == 204


def test_members_add_change_remove_with_audit(client_for: ClientFor) -> None:
    owner = MembershipFactory.create(role=Role.OWNER)
    org = owner.org
    newcomer = UserFactory.create(email="new@example.com")
    client = client_for(owner.user)
    base = f"/api/v1/orgs/{org.slug}/members/"

    added = client.post(base, {"email": "NEW@example.com", "role": "viewer"})
    assert added.status_code == 201
    member_id = added.json()["id"]
    assert client.post(base, {"email": "new@example.com", "role": "viewer"}).status_code == 400
    assert client.post(base, {"email": "ghost@example.com", "role": "viewer"}).status_code == 400

    changed = client.patch(f"{base}{member_id}/", {"role": "member"})
    assert changed.json()["role"] == "member"
    assert client.delete(f"{base}{member_id}/").status_code == 204
    assert not Membership.objects.filter(user=newcomer).exists()

    actions = list(AuditLog.objects.filter(org=org).values_list("action", flat=True))
    assert actions == ["member.remove", "member.role_change", "member.add"]
    log = client.get(f"/api/v1/orgs/{org.slug}/audit-log/").json()
    assert log["results"][0]["action"] == "member.remove"
    assert log["results"][0]["actor"] == owner.user.email


def test_only_owners_touch_owner_role(client_for: ClientFor) -> None:
    owner = MembershipFactory.create(role=Role.OWNER)
    admin = MembershipFactory.create(org=owner.org, role=Role.ADMIN)
    UserFactory.create(email="boss@example.com")
    client = client_for(admin.user)
    base = f"/api/v1/orgs/{owner.org.slug}/members/"

    assert client.post(base, {"email": "boss@example.com", "role": "owner"}).status_code == 403
    assert client.patch(f"{base}{owner.pk}/", {"role": "viewer"}).status_code == 403
    assert client.delete(f"{base}{owner.pk}/").status_code == 403
    assert client.patch(f"{base}{admin.pk}/", {"role": "owner"}).status_code == 403


def test_last_owner_cannot_leave_or_be_demoted(client_for: ClientFor) -> None:
    owner = MembershipFactory.create(role=Role.OWNER)
    client = client_for(owner.user)
    base = f"/api/v1/orgs/{owner.org.slug}/members/"
    assert client.patch(f"{base}{owner.pk}/", {"role": "admin"}).status_code == 400
    assert client.delete(f"{base}{owner.pk}/").status_code == 400

    second = MembershipFactory.create(org=owner.org, role=Role.OWNER)
    assert client.patch(f"{base}{second.pk}/", {"role": "admin"}).status_code == 200


def test_viewer_reads_but_cannot_write_and_audit_log_is_admin_only(
    client_for: ClientFor,
) -> None:
    viewer = MembershipFactory.create(role=Role.VIEWER)
    client = client_for(viewer.user)
    slug = viewer.org.slug
    assert client.get(f"/api/v1/orgs/{slug}/members/").status_code == 200
    assert client.post(f"/api/v1/orgs/{slug}/members/", {}).status_code == 403
    assert client.get(f"/api/v1/orgs/{slug}/audit-log/").status_code == 403
