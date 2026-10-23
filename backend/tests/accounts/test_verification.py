import json
import re
from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import captcha, codes
from apps.accounts.models import EmailCode, User
from apps.notifications.models import DigestSubscription
from tests.factories import PASSWORD, CalendarFactory, MembershipFactory, OrgFactory, UserFactory

pytestmark = pytest.mark.django_db
SIGNUP = "/api/v1/auth/signup/"
VERIFY = "/api/v1/auth/verify/"


@pytest.fixture(autouse=True)
def fresh_throttles() -> None:
    cache.clear()


def emailed_code() -> str:
    match = re.search(r"\b(\d{6})\b", str(mail.outbox[-1].body))
    assert match
    return match.group(1)


def signup(client: APIClient, email: str = "new@example.com", **extra: Any) -> Any:
    return client.post(SIGNUP, {"email": email, "password": PASSWORD, **extra}, format="json")


def test_code_confirms_the_address_and_signs_in(client: APIClient) -> None:
    signup(client)
    assert "Confirm" in mail.outbox[-1].subject
    response = client.post(VERIFY, {"email": "NEW@example.com", "code": emailed_code()})
    assert response.status_code == 200
    assert response.json()["email_verified"] is True
    assert client.get("/api/v1/auth/me/").json()["email"] == "new@example.com"
    assert "Welcome" in mail.outbox[-1].subject
    stored = EmailCode.objects.get(user__email="new@example.com", purpose="verify")
    assert stored.used_at is not None


def test_signup_answers_the_same_for_taken_addresses(client: APIClient) -> None:
    owner = UserFactory.create(email="taken@example.com")
    taken = signup(client, "taken@example.com", name="Mallory")
    fresh = signup(client, "fresh@example.com")
    assert taken.status_code == fresh.status_code == 202
    assert taken.json() == fresh.json()
    note = next(m for m in mail.outbox if m.to == ["taken@example.com"])
    assert "tried to sign up" in note.subject
    assert not re.search(r"\b\d{6}\b", str(note.body))
    owner.refresh_from_db()
    assert owner.check_password(PASSWORD)
    assert owner.name != "Mallory"


def test_a_squatted_unverified_address_goes_to_whoever_proves_it(client: APIClient) -> None:
    signup(client, "victim@example.com", password="squatter-password-1")
    signup(client, "victim@example.com")
    user = User.objects.get(email="victim@example.com")
    assert user.check_password(PASSWORD)
    first_code = re.search(r"\b(\d{6})\b", str(mail.outbox[0].body))
    assert first_code
    stale = client.post(VERIFY, {"email": user.email, "code": first_code.group(1)})
    assert stale.status_code == 400
    assert client.post(VERIFY, {"email": user.email, "code": emailed_code()}).status_code == 200


def test_unverified_login_sends_a_code_instead_of_signing_in(client: APIClient) -> None:
    UserFactory.create(email="later@example.com", email_verified_at=None)
    body = {"email": "later@example.com", "password": PASSWORD}
    response = client.post("/api/v1/auth/login/", body)
    assert response.status_code == 202
    assert response.json()["verification_required"] is True
    assert client.get("/api/v1/auth/me/").status_code == 204
    verified = client.post(VERIFY, {"email": "later@example.com", "code": emailed_code()})
    assert verified.status_code == 200


def test_wrong_codes_burn_out_and_expired_codes_fail(client: APIClient) -> None:
    signup(client)
    code = emailed_code()
    wrong = f"{(int(code) + 1) % 10**6:06d}"
    for _ in range(codes.MAX_ATTEMPTS):
        assert client.post(VERIFY, {"email": "new@example.com", "code": wrong}).status_code == 400
    assert client.post(VERIFY, {"email": "new@example.com", "code": code}).status_code == 400
    client.post("/api/v1/auth/verify/resend/", {"email": "new@example.com"})
    EmailCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    response = client.post(VERIFY, {"email": "new@example.com", "code": emailed_code()})
    assert response.status_code == 400


def test_emails_to_one_address_are_capped_per_hour(client: APIClient) -> None:
    for _ in range(5):
        client.post("/api/v1/auth/verify/resend/", {"email": "x@example.com"})
        signup(client)
    assert len([m for m in mail.outbox if m.to == ["new@example.com"]]) == codes.PER_EMAIL_PER_HOUR


def test_honeypot_answers_like_success_and_does_nothing(client: APIClient) -> None:
    response = signup(client, website="http://spam.example")
    assert response.status_code == 202
    assert not User.objects.filter(email="new@example.com").exists()
    assert mail.outbox == []


def test_unverified_accounts_cannot_reach_other_people(client: APIClient) -> None:
    user = UserFactory.create(email_verified_at=None)
    org = OrgFactory.create()
    MembershipFactory.create(user=user, org=org, role="owner")
    calendar = CalendarFactory.create(org=org)
    client.force_login(user)
    assert client.post("/api/v1/orgs/", {"name": "Acme"}).status_code == 403
    invite = client.post(
        f"/api/v1/orgs/{org.slug}/invites/", {"email": "a@example.com", "role": "member"}
    )
    assert invite.status_code == 403
    digest = client.put(f"/api/v1/orgs/{org.slug}/calendars/{calendar.id}/digest/")
    assert digest.status_code == 403
    assert not DigestSubscription.objects.exists()


def test_members_are_only_added_by_a_confirmed_address(client: APIClient) -> None:
    admin = UserFactory.create()
    org = OrgFactory.create()
    MembershipFactory.create(user=admin, org=org, role="admin")
    UserFactory.create(email="pending@example.com", email_verified_at=None)
    client.force_login(admin)
    response = client.post(
        f"/api/v1/orgs/{org.slug}/members/", {"email": "pending@example.com", "role": "viewer"}
    )
    assert response.status_code == 400


def test_reset_proves_the_mailbox_too(client: APIClient) -> None:
    user = UserFactory.create(email_verified_at=None)
    client.post("/api/v1/auth/password/forgot/", {"email": user.email})
    body = {"email": user.email, "code": emailed_code(), "password": "a-new-long-passphrase-9"}
    assert client.post("/api/v1/auth/password/reset/", body).status_code == 200
    user.refresh_from_db()
    assert user.email_verified


def test_prune_removes_only_stale_unclaimed_signups() -> None:
    old = timezone.now() - timedelta(days=8)
    stale = UserFactory.create(email_verified_at=None, date_joined=old)
    member = UserFactory.create(email_verified_at=None, date_joined=old)
    MembershipFactory.create(user=member)
    UserFactory.create(email_verified_at=None)
    UserFactory.create(date_joined=old)
    assert codes.prune_unverified() == 1
    assert not User.objects.filter(pk=stale.pk).exists()


def test_security_changes_are_emailed(client: APIClient) -> None:
    user = UserFactory.create()
    user.identities.create(provider="google", subject="1", email=user.email, email_verified=True)
    client.force_login(user)
    assert client.delete("/api/v1/auth/identities/google/").status_code == 204
    assert "Security alert" in mail.outbox[-1].subject
    assert "removed" in str(mail.outbox[-1].body)


def test_signed_out_me_is_not_an_error(client: APIClient) -> None:
    assert client.get("/api/v1/auth/me/").status_code == 204
    assert client.patch("/api/v1/auth/me/", {"name": "x"}).status_code == 403


class FakeGoogle:
    def __init__(self, answers: dict[str, dict[str, Any]]) -> None:
        self.answers = answers
        self.calls: list[str] = []

    def __call__(self, request: Any, timeout: int) -> Any:
        token = dict(p.split("=") for p in request.data.decode().split("&"))["response"]
        self.calls.append(token)
        body = json.dumps(self.answers[token]).encode()
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = body
        return response


@pytest.fixture
def recaptcha(settings: Any) -> None:
    settings.RECAPTCHA = {"v3_site": "s3", "v3_secret": "k3", "v2_site": "s2", "v2_secret": "k2"}


@pytest.mark.usefixtures("recaptcha")
def test_low_v3_score_asks_for_the_checkbox(client: APIClient) -> None:
    google = FakeGoogle(
        {
            "human": {"success": True, "action": "signup", "score": 0.9},
            "bot": {"success": True, "action": "signup", "score": 0.1},
            "other-action": {"success": True, "action": "login", "score": 0.9},
            "ticked": {"success": True},
        }
    )
    with mock.patch("urllib.request.urlopen", google):
        assert signup(client, "a@example.com", captcha_v3="human").status_code == 202
        low = signup(client, "b@example.com", captcha_v3="bot")
        assert low.status_code == 400
        assert low.json()["captcha"] == "v2"
        assert signup(client, "c@example.com", captcha_v3="other-action").status_code == 400
        assert signup(client, "d@example.com").status_code == 400
        assert signup(client, "b@example.com", captcha_v2="ticked").status_code == 202
    assert set(User.objects.values_list("email", flat=True)) == {"a@example.com", "b@example.com"}


@pytest.mark.usefixtures("recaptcha")
def test_google_unreachable_falls_back_to_the_checkbox(client: APIClient) -> None:
    with mock.patch("urllib.request.urlopen", side_effect=TimeoutError):
        response = client.post(
            "/api/v1/auth/password/forgot/", {"email": "x@example.com", "captcha_v3": "t"}
        )
    assert response.status_code == 400
    assert response.json()["captcha"] == "v2"


def test_site_keys_are_public_and_secrets_are_not(client: APIClient, settings: Any) -> None:
    assert client.get("/api/v1/auth/captcha/").json() == {"v3": None, "v2": None}
    settings.RECAPTCHA = {"v3_site": "s3", "v3_secret": "k3", "v2_site": "", "v2_secret": ""}
    assert client.get("/api/v1/auth/captcha/").json() == {"v3": "s3", "v2": None}
    assert captcha.check({}, "signup", None) == "failed"
