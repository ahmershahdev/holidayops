import re

import pytest
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import UserSession
from apps.accounts.sessions import describe
from tests.factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db
CHROME_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0 Safari/537.36"
)
SAFARI_IOS = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)


@pytest.fixture(autouse=True)
def fresh_cache() -> None:
    cache.clear()


def signed_in(email: str, agent: str) -> APIClient:
    client = APIClient(HTTP_USER_AGENT=agent)
    response = client.post("/api/v1/auth/login/", {"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return client


def test_each_login_is_listed_with_its_device() -> None:
    user = UserFactory.create()
    laptop = signed_in(user.email, CHROME_WIN)
    signed_in(user.email, SAFARI_IOS)
    rows = laptop.get("/api/v1/auth/sessions/").json()
    assert len(rows) == 2
    devices = {(r["browser"], r["system"], r["current"]) for r in rows}
    assert devices == {("Chrome", "Windows", True), ("Safari", "iOS", False)}
    assert all(r["ip"] == "127.0.0.1" for r in rows)


def test_signing_out_others_keeps_this_device() -> None:
    user = UserFactory.create()
    laptop = signed_in(user.email, CHROME_WIN)
    phone = signed_in(user.email, SAFARI_IOS)
    assert laptop.post("/api/v1/auth/sessions/others/").json() == {"ended": 1}
    assert phone.get("/api/v1/auth/me/").status_code == 204
    assert laptop.get("/api/v1/auth/me/").status_code == 200
    assert len(laptop.get("/api/v1/auth/sessions/").json()) == 1


def test_one_device_can_be_signed_out_but_not_someone_elses() -> None:
    user = UserFactory.create()
    other = UserFactory.create()
    laptop = signed_in(user.email, CHROME_WIN)
    phone = signed_in(user.email, SAFARI_IOS)
    signed_in(other.email, CHROME_WIN)
    theirs = UserSession.objects.get(user=other)
    assert laptop.delete(f"/api/v1/auth/sessions/{theirs.pk}/").status_code == 404
    assert Session.objects.filter(session_key=theirs.session_key).exists()
    mine = UserSession.objects.get(user=user, user_agent=SAFARI_IOS)
    assert laptop.delete(f"/api/v1/auth/sessions/{mine.pk}/").status_code == 204
    assert phone.get("/api/v1/auth/me/").status_code == 204
    current = UserSession.objects.get(user=user)
    assert laptop.delete(f"/api/v1/auth/sessions/{current.pk}/").status_code == 404


def test_logout_and_password_reset_end_sessions(client: APIClient) -> None:
    user = UserFactory.create()
    laptop = signed_in(user.email, CHROME_WIN)
    signed_in(user.email, SAFARI_IOS)
    laptop.post("/api/v1/auth/logout/")
    assert UserSession.objects.filter(user=user).count() == 1
    client.post("/api/v1/auth/password/forgot/", {"email": user.email})
    match = re.search(r"\b(\d{6})\b", str(mail.outbox[-1].body))
    assert match
    body = {"email": user.email, "code": match.group(1), "password": "a-new-long-passphrase-7"}
    assert client.post("/api/v1/auth/password/reset/", body).status_code == 200
    assert UserSession.objects.filter(user=user).count() == 1
    assert UserSession.objects.get(user=user).session_key == client.session.session_key


def test_expired_sessions_drop_out_of_the_list() -> None:
    user = UserFactory.create()
    laptop = signed_in(user.email, CHROME_WIN)
    phone = signed_in(user.email, SAFARI_IOS)
    Session.objects.filter(session_key=phone.session.session_key).delete()
    assert len(laptop.get("/api/v1/auth/sessions/").json()) == 1
    assert UserSession.objects.filter(user=user).count() == 1


def test_sessions_need_a_signed_in_user(client: APIClient) -> None:
    assert client.get("/api/v1/auth/sessions/").status_code == 403
    assert client.post("/api/v1/auth/sessions/others/").status_code == 403


@pytest.mark.parametrize(
    ("agent", "expected"),
    [
        (CHROME_WIN, ("Chrome", "Windows")),
        (SAFARI_IOS, ("Safari", "iOS")),
        (
            "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
            ("Firefox", "Linux"),
        ),
        (CHROME_WIN.replace("Safari/537.36", "Safari/537.36 Edg/141.0"), ("Edge", "Windows")),
        ("curl/8.0", ("", "")),
    ],
)
def test_user_agents_are_described(agent: str, expected: tuple[str, str]) -> None:
    assert describe(agent) == expected
