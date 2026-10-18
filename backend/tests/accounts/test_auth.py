from typing import Any

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from config.security_log import email_ref
from config.settings import base as base_settings
from tests.factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def test_signup_logs_in_and_hashes_with_argon2(client: APIClient, settings: Any) -> None:
    settings.PASSWORD_HASHERS = base_settings.PASSWORD_HASHERS
    response = client.post(
        "/api/v1/auth/signup/",
        {"email": "Ayesha@Example.com", "password": PASSWORD, "name": "Ayesha"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "ayesha@example.com"
    user = User.objects.get(email="ayesha@example.com")
    assert user.password.startswith("argon2")
    assert client.get("/api/v1/auth/me/").json()["email"] == "ayesha@example.com"


def test_signup_rejects_duplicate_email_and_weak_password(client: APIClient) -> None:
    UserFactory.create(email="taken@example.com")
    duplicate = client.post(
        "/api/v1/auth/signup/", {"email": "TAKEN@example.com", "password": PASSWORD}
    )
    assert "email" in duplicate.json()
    weak = client.post("/api/v1/auth/signup/", {"email": "new@example.com", "password": "12345"})
    assert weak.status_code == 400


def test_login_logout_cycle(client: APIClient) -> None:
    UserFactory.create(email="sam@example.com")
    bad = client.post("/api/v1/auth/login/", {"email": "sam@example.com", "password": "wrong"})
    assert bad.status_code == 400
    ok = client.post("/api/v1/auth/login/", {"email": "SAM@example.com", "password": PASSWORD})
    assert ok.status_code == 200
    assert client.get("/api/v1/auth/me/").status_code == 200
    assert client.post("/api/v1/auth/logout/").status_code == 204
    assert client.get("/api/v1/auth/me/").status_code == 403


def test_session_writes_require_csrf() -> None:
    UserFactory.create(email="csrf@example.com")
    client = APIClient(enforce_csrf_checks=True)
    body = {"email": "csrf@example.com", "password": PASSWORD}
    # Login CSRF: without a token another site could sign the browser into its own account.
    assert client.post("/api/v1/auth/login/", body).status_code == 403
    token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
    assert client.post("/api/v1/auth/login/", body, HTTP_X_CSRFTOKEN=token).status_code == 200
    assert client.post("/api/v1/orgs/", {"name": "Acme"}).status_code == 403
    token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
    response = client.post("/api/v1/orgs/", {"name": "Acme"}, HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 201


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/signup/",
        "/api/v1/auth/password/forgot/",
        "/api/v1/auth/password/reset/",
        "/api/v1/auth/2fa/verify/",
    ],
)
def test_anonymous_auth_posts_need_a_csrf_token(path: str) -> None:
    assert APIClient(enforce_csrf_checks=True).post(path, {}).status_code == 403


def test_one_account_locks_after_ten_failed_logins(client: APIClient) -> None:
    UserFactory.create(email="target@example.com")
    cache.set(f"login-failures:{email_ref('target@example.com')}", 10)
    body = {"email": "target@example.com", "password": PASSWORD}
    assert client.post("/api/v1/auth/login/", body).status_code == 429
    cache.delete(f"login-failures:{email_ref('target@example.com')}")
    assert client.post("/api/v1/auth/login/", body).status_code == 200


def test_login_is_throttled(client: APIClient) -> None:
    for _ in range(10):
        client.post("/api/v1/auth/login/", {"email": "x@example.com", "password": "nope"})
    response = client.post("/api/v1/auth/login/", {"email": "x@example.com", "password": "nope"})
    assert response.status_code == 429


def test_signup_records_the_ui_language(client: APIClient) -> None:
    body = {"email": "urdu@example.com", "password": PASSWORD}
    response = client.post("/api/v1/auth/signup/", body, HTTP_ACCEPT_LANGUAGE="ur")
    assert response.data["language"] == "ur"
    other = {"email": "fr@example.com", "password": PASSWORD}
    assert (
        client.post("/api/v1/auth/signup/", other, HTTP_ACCEPT_LANGUAGE="fr").data["language"]
        == "en"
    )


def test_me_can_change_name_and_language_but_not_email(client: APIClient) -> None:
    client.post("/api/v1/auth/signup/", {"email": "me@example.com", "password": PASSWORD})
    response = client.patch(
        "/api/v1/auth/me/",
        {"name": "Ahmer", "language": "ar", "email": "x@example.com"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["name"] == "Ahmer"
    assert response.data["language"] == "ar"
    assert response.data["email"] == "me@example.com"
    bad = client.patch("/api/v1/auth/me/", {"language": "fr"}, format="json")
    assert bad.status_code == 400
