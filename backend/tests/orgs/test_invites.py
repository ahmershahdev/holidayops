import re
from collections.abc import Callable
from datetime import timedelta
from smtplib import SMTPException
from typing import Any
from unittest import mock

import pytest
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.orgs.invite_views import MAX_PENDING_INVITES
from apps.orgs.invites import hash_token
from apps.orgs.models import AuditLog, Invite, Membership, Role
from tests.factories import MembershipFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(client_for: Callable[[User], APIClient]) -> dict[str, Any]:
    membership = MembershipFactory.create(role=Role.ADMIN, user__name="Ayesha")
    url = f"/api/v1/orgs/{membership.org.slug}/invites/"
    return {"membership": membership, "url": url, "api": client_for(membership.user)}


def last_body() -> str:
    return str(mail.outbox[-1].body)


def last_html() -> str:
    message = mail.outbox[-1]
    assert isinstance(message, EmailMultiAlternatives)
    return str(message.alternatives[0][0])


def invite(admin: dict[str, Any], email: str = "new@example.com", role: str = "member") -> str:
    response = admin["api"].post(admin["url"], {"email": email, "role": role}, format="json")
    assert response.status_code == 201, response.data
    match = re.search(r"/invite\?token=([\w-]+)", last_body())
    assert match is not None
    return match.group(1)


def test_invite_emails_a_one_time_link(admin: dict[str, Any]) -> None:
    token = invite(admin, "New@Example.com")
    message = mail.outbox[0]
    assert message.to == ["new@example.com"]
    assert message.subject == f"You're invited to {admin['membership'].org.name} on HolidayOps"
    assert "Ayesha invited you to join" in message.body
    assert "as Member" in message.body
    assert f"{settings.APP_URL}/invite?token={token}" in message.body
    stored = Invite.objects.get()
    assert stored.token_hash == hash_token(token)
    assert stored.email == "new@example.com"
    assert stored.expires_at > timezone.now() + timedelta(days=6)
    listed = admin["api"].get(admin["url"]).data
    assert [(i["email"], i["role"]) for i in listed] == [("new@example.com", "member")]
    assert AuditLog.objects.filter(action="invite.create").count() == 1


def test_only_admins_invite_and_only_owners_invite_owners(
    admin: dict[str, Any], client_for: Callable[[User], APIClient]
) -> None:
    member = MembershipFactory.create(org=admin["membership"].org, role=Role.MEMBER)
    body = {"email": "x@example.com", "role": "viewer"}
    assert client_for(member.user).post(admin["url"], body, format="json").status_code == 403
    assert client_for(member.user).get(admin["url"]).status_code == 403
    owner_body = {"email": "x@example.com", "role": "owner"}
    assert admin["api"].post(admin["url"], owner_body, format="json").status_code == 403
    owner = MembershipFactory.create(org=admin["membership"].org, role=Role.OWNER)
    assert client_for(owner.user).post(admin["url"], owner_body, format="json").status_code == 201


def test_members_cannot_be_invited(admin: dict[str, Any]) -> None:
    body = {"email": admin["membership"].user.email.upper(), "role": "viewer"}
    assert admin["api"].post(admin["url"], body, format="json").status_code == 400


def test_reinviting_replaces_the_pending_invite(admin: dict[str, Any]) -> None:
    old = invite(admin, role="viewer")
    new = invite(admin, role="admin")
    assert Invite.objects.count() == 1
    assert Invite.objects.get().role == "admin"
    assert APIClient().get(f"/api/v1/invites/{old}/").status_code == 404
    assert APIClient().get(f"/api/v1/invites/{new}/").status_code == 200


def test_pending_invite_limit(admin: dict[str, Any]) -> None:
    org = admin["membership"].org
    Invite.objects.bulk_create(
        Invite(
            org=org,
            email=f"p{n}@example.com",
            role="viewer",
            token_hash=f"{n:064d}",
            expires_at=timezone.now() + timedelta(days=1),
        )
        for n in range(MAX_PENDING_INVITES)
    )
    body = {"email": "one-more@example.com", "role": "viewer"}
    assert admin["api"].post(admin["url"], body, format="json").status_code == 400


def test_preview_needs_no_login(admin: dict[str, Any]) -> None:
    token = invite(admin, role="viewer")
    data = APIClient().get(f"/api/v1/invites/{token}/").data
    assert data == {
        "org_name": admin["membership"].org.name,
        "org_slug": admin["membership"].org.slug,
        "email": "new@example.com",
        "role": "viewer",
        "invited_by": "Ayesha",
        "expires_at": data["expires_at"],
    }
    assert APIClient().get("/api/v1/invites/not-a-token/").status_code == 404


def test_expired_invites_are_404(admin: dict[str, Any]) -> None:
    token = invite(admin)
    Invite.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert APIClient().get(f"/api/v1/invites/{token}/").status_code == 404
    assert admin["api"].get(admin["url"]).data == []


def test_accept_with_the_invited_account(
    admin: dict[str, Any], client_for: Callable[[User], APIClient]
) -> None:
    token = invite(admin, role="admin")
    newcomer = UserFactory.create(email="NEW@example.com")
    response = client_for(newcomer).post(f"/api/v1/invites/{token}/accept/")
    assert response.status_code == 200
    assert response.data["slug"] == admin["membership"].org.slug
    assert response.data["role"] == "admin"
    membership = Membership.objects.get(user=newcomer)
    assert membership.role == "admin"
    assert AuditLog.objects.filter(action="invite.accept", actor=newcomer).count() == 1
    assert client_for(newcomer).post(f"/api/v1/invites/{token}/accept/").status_code == 404
    assert APIClient().get(f"/api/v1/invites/{token}/").status_code == 404


def test_accept_needs_login_and_the_matching_email(
    admin: dict[str, Any], client_for: Callable[[User], APIClient]
) -> None:
    token = invite(admin)
    assert APIClient().post(f"/api/v1/invites/{token}/accept/").status_code == 403
    stranger = UserFactory.create(email="forwarded@example.com")
    response = client_for(stranger).post(f"/api/v1/invites/{token}/accept/")
    assert response.status_code == 403
    assert "new@example.com" in str(response.data)
    assert not Membership.objects.filter(user=stranger).exists()
    assert Invite.objects.get().accepted_at is None


def test_accepting_when_already_a_member_keeps_the_existing_role(
    admin: dict[str, Any], client_for: Callable[[User], APIClient]
) -> None:
    token = invite(admin, role="admin")
    user = UserFactory.create(email="new@example.com")
    Membership.objects.create(user=user, org=admin["membership"].org, role=Role.VIEWER)
    assert client_for(user).post(f"/api/v1/invites/{token}/accept/").status_code == 200
    assert Membership.objects.get(user=user).role == "viewer"


def test_resend_issues_a_new_link(admin: dict[str, Any]) -> None:
    old = invite(admin)
    pk = Invite.objects.get().pk
    assert admin["api"].post(f"{admin['url']}{pk}/resend/").status_code == 200
    assert len(mail.outbox) == 2
    new = re.search(r"/invite\?token=([\w-]+)", last_body())
    assert new is not None
    assert new.group(1) != old
    assert APIClient().get(f"/api/v1/invites/{old}/").status_code == 404
    assert APIClient().get(f"/api/v1/invites/{new.group(1)}/").status_code == 200


def test_revoke_kills_the_link(admin: dict[str, Any]) -> None:
    token = invite(admin)
    pk = Invite.objects.get().pk
    assert admin["api"].delete(f"{admin['url']}{pk}/").status_code == 204
    assert APIClient().get(f"/api/v1/invites/{token}/").status_code == 404
    assert AuditLog.objects.filter(action="invite.revoke").count() == 1


def test_failed_email_leaves_no_invite_behind(admin: dict[str, Any]) -> None:
    with mock.patch(
        "django.core.mail.EmailMultiAlternatives.send", side_effect=SMTPException("down")
    ):
        response = admin["api"].post(
            admin["url"], {"email": "new@example.com", "role": "viewer"}, format="json"
        )
    assert response.status_code == 503
    assert not Invite.objects.exists()
    assert not AuditLog.objects.filter(action="invite.create").exists()


def test_email_language_follows_the_invitee_or_the_inviter(admin: dict[str, Any]) -> None:
    UserFactory.create(email="urdu@example.com", language="ur")
    invite(admin, "urdu@example.com")
    assert not mail.outbox[-1].subject.startswith("You're invited")
    assert 'dir="rtl"' in last_html()

    admin["api"].post(
        admin["url"],
        {"email": "nobody@example.com", "role": "viewer"},
        format="json",
        HTTP_ACCEPT_LANGUAGE="ar",
    )
    assert 'lang="ar"' in last_html()


def test_inviting_is_throttled(admin: dict[str, Any]) -> None:
    for n in range(30):
        invite(admin, f"t{n}@example.com")
    body = {"email": "t31@example.com", "role": "viewer"}
    assert admin["api"].post(admin["url"], body, format="json").status_code == 429
