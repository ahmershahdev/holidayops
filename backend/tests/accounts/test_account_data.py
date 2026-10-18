import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.orgs.models import AuditLog, Membership, Organization, Role
from tests.factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fresh_throttles() -> None:
    cache.clear()


def org_with(*members: tuple[User, Role]) -> Organization:
    org = Organization.objects.create(name="Acme", slug=f"acme-{Organization.objects.count()}")
    for user, role in members:
        Membership.objects.create(user=user, org=org, role=role)
    return org


def test_export_has_the_account_and_no_secrets() -> None:
    user = UserFactory.create(email="me@x.com")
    org_with((user, Role.OWNER))
    client = APIClient()
    client.force_login(user)
    response = client.get("/api/v1/auth/me/export/")
    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    data = response.json()
    assert data["account"]["email"] == "me@x.com"
    assert data["organizations"][0]["role"] == "owner"
    text = response.content.decode()
    assert "password" not in text
    assert "key_hash" not in text


def test_delete_needs_the_email_and_password() -> None:
    user = UserFactory.create(email="me@x.com")
    client = APIClient()
    client.force_login(user)
    wrong_email = client.post("/api/v1/auth/me/delete/", {"password": PASSWORD, "confirm": "x"})
    assert "confirm" in wrong_email.json()
    wrong_password = client.post(
        "/api/v1/auth/me/delete/", {"password": "nope", "confirm": "ME@x.com"}
    )
    assert "password" in wrong_password.json()
    assert User.objects.filter(pk=user.pk).exists()


def test_delete_removes_solo_orgs_and_keeps_shared_history() -> None:
    user = UserFactory.create(email="me@x.com")
    friend = UserFactory.create()
    solo = org_with((user, Role.OWNER))
    shared = org_with((friend, Role.OWNER), (user, Role.ADMIN))
    AuditLog.objects.create(org=shared, actor=user, action="calendar.created", target="x")
    client = APIClient()
    client.force_login(user)
    response = client.post("/api/v1/auth/me/delete/", {"password": PASSWORD, "confirm": user.email})
    assert response.status_code == 204
    assert not User.objects.filter(pk=user.pk).exists()
    assert not Organization.objects.filter(pk=solo.pk).exists()
    assert Organization.objects.filter(pk=shared.pk).exists()
    assert AuditLog.objects.get(org=shared).actor is None
    assert client.get("/api/v1/auth/me/").status_code == 403


def test_sole_owner_of_a_shared_org_must_hand_it_over_first() -> None:
    user = UserFactory.create()
    org_with((user, Role.OWNER), (UserFactory.create(), Role.MEMBER))
    client = APIClient()
    client.force_login(user)
    response = client.post("/api/v1/auth/me/delete/", {"password": PASSWORD, "confirm": user.email})
    assert response.status_code == 409
    assert "Acme" in response.json()["detail"]
