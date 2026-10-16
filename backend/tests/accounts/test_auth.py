import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from tests.factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def test_signup_logs_in_and_hashes_with_argon2(client: APIClient) -> None:
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
    login = client.post("/api/v1/auth/login/", {"email": "csrf@example.com", "password": PASSWORD})
    assert login.status_code == 200
    assert client.post("/api/v1/orgs/", {"name": "Acme"}).status_code == 403
    token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
    response = client.post("/api/v1/orgs/", {"name": "Acme"}, HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 201


def test_login_is_throttled(client: APIClient) -> None:
    for _ in range(10):
        client.post("/api/v1/auth/login/", {"email": "x@example.com", "password": "nope"})
    response = client.post("/api/v1/auth/login/", {"email": "x@example.com", "password": "nope"})
    assert response.status_code == 429
