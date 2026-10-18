import json
import re
from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.core import mail
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts import resets
from apps.accounts.models import PasswordResetCode
from apps.notifications.resend import ResendEmailBackend
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db
NEW_PASSWORD = "a-much-longer-passphrase-2027"


@pytest.fixture(autouse=True)
def fresh_throttles() -> None:
    cache.clear()


def emailed_code() -> str:
    match = re.search(r"\b(\d{6})\b", str(mail.outbox[-1].body))
    assert match
    return match.group(1)


def test_forgot_answers_the_same_for_unknown_addresses(client: APIClient) -> None:
    UserFactory.create(email="known@example.com")
    known = client.post("/api/v1/auth/password/forgot/", {"email": "KNOWN@example.com"})
    unknown = client.post("/api/v1/auth/password/forgot/", {"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["known@example.com"]


def test_code_is_stored_only_as_a_keyed_hash(client: APIClient) -> None:
    user = UserFactory.create()
    client.post("/api/v1/auth/password/forgot/", {"email": user.email})
    code = emailed_code()
    stored = PasswordResetCode.objects.get(user=user)
    assert code not in stored.code_hash
    assert stored.code_hash == resets.code_hash(user.pk, code)
    assert stored.expires_at - stored.created_at <= timedelta(minutes=10)


def test_reset_logs_in_works_once_and_signs_out_other_sessions(client: APIClient) -> None:
    user = UserFactory.create()
    other = APIClient()
    other.force_login(user)
    client.post("/api/v1/auth/password/forgot/", {"email": user.email})
    body = {"email": user.email, "code": emailed_code(), "password": NEW_PASSWORD}
    response = client.post("/api/v1/auth/password/reset/", body)
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me/").status_code == 200
    assert other.get("/api/v1/auth/me/").status_code == 403
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert "changed" in mail.outbox[-1].subject
    again = APIClient().post("/api/v1/auth/password/reset/", body)
    assert again.status_code == 400


def test_expired_code_fails(client: APIClient) -> None:
    user = UserFactory.create()
    client.post("/api/v1/auth/password/forgot/", {"email": user.email})
    PasswordResetCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    body = {"email": user.email, "code": emailed_code(), "password": NEW_PASSWORD}
    assert client.post("/api/v1/auth/password/reset/", body).status_code == 400


def test_five_wrong_guesses_burn_the_code() -> None:
    user = UserFactory.create()
    resets.request_reset(user.email)
    code = emailed_code()
    wrong = f"{(int(code) + 1) % 10**6:06d}"
    for _ in range(resets.MAX_ATTEMPTS):
        assert resets.reset_password(user.email, wrong, NEW_PASSWORD) is None
    assert resets.reset_password(user.email, code, NEW_PASSWORD) is None


def test_a_new_code_replaces_the_old_one_and_the_hourly_limit_holds() -> None:
    user = UserFactory.create()
    assert resets.request_reset(user.email)
    first = emailed_code()
    assert resets.request_reset(user.email)
    assert resets.reset_password(user.email, first, NEW_PASSWORD) is None
    assert resets.request_reset(user.email)
    assert not resets.request_reset(user.email)
    assert len(mail.outbox) == resets.PER_EMAIL_PER_HOUR


def test_malformed_codes_are_refused(client: APIClient) -> None:
    user = UserFactory.create()
    assert resets.reset_password(user.email, "12ab56", NEW_PASSWORD) is None
    body = {"email": user.email, "code": "1234567", "password": NEW_PASSWORD}
    assert "code" in client.post("/api/v1/auth/password/reset/", body).json()


def test_weak_new_password_is_refused(client: APIClient) -> None:
    user = UserFactory.create()
    body = {"email": user.email, "code": "123456", "password": "short"}
    assert "non_field_errors" in client.post("/api/v1/auth/password/reset/", body).json()


def test_forgot_is_rate_limited_per_ip(client: APIClient) -> None:
    with mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"password_reset": "2/hour"}):
        codes = [
            client.post("/api/v1/auth/password/forgot/", {"email": "x@example.com"}).status_code
            for _ in range(3)
        ]
    assert codes == [202, 202, 429]


def test_code_email_escapes_and_is_translated() -> None:
    user = UserFactory.create(language="ar")
    resets.request_reset(user.email)
    message = mail.outbox[-1]
    assert isinstance(message, EmailMultiAlternatives)
    html = message.alternatives[0][0]
    assert 'dir="rtl"' in str(html)
    assert emailed_code() in str(html)


def test_resend_backend_posts_the_message(settings: Any) -> None:
    settings.RESEND_API_KEY = "re_test"
    message = EmailMultiAlternatives("Hi", "Plain", "HolidayOps <a@ahmershah.dev>", ["b@x.com"])
    message.attach_alternative("<p>Hi</p>", "text/html")
    with mock.patch("urllib.request.urlopen") as urlopen:
        assert ResendEmailBackend().send_messages([message]) == 1
    request = urlopen.call_args.args[0]
    assert request.full_url == "https://api.resend.com/emails"
    assert request.headers["Authorization"] == "Bearer re_test"
    data = json.loads(request.data)
    assert data == {
        "from": "HolidayOps <a@ahmershah.dev>",
        "to": ["b@x.com"],
        "subject": "Hi",
        "text": "Plain",
        "html": "<p>Hi</p>",
    }
